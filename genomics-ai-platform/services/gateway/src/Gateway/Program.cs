using System.Security.Claims;
using System.Text;
using System.Threading.RateLimiting;
using Gateway;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using Microsoft.IdentityModel.Tokens;

var builder = WebApplication.CreateBuilder(args);

var aiOpts = builder.Configuration.GetSection("AiService").Get<AiServiceOptions>() ?? new();
var jwt = builder.Configuration.GetSection("Jwt").Get<JwtOptions>() ?? new();

// Fail fast on insecure defaults outside Development (same rule as the Python service).
if (!builder.Environment.IsDevelopment() && !builder.Environment.IsEnvironment("Testing"))
{
    if (aiOpts.InternalKey == "dev-internal-key" || jwt.SigningKey.StartsWith("dev-only"))
        throw new InvalidOperationException("Refusing to start with default secrets outside Development.");
}
if (Encoding.UTF8.GetByteCount(jwt.SigningKey) < 32)
    throw new InvalidOperationException("Jwt:SigningKey must be at least 32 bytes.");

builder.Services.AddSingleton(aiOpts);
builder.Services.AddSingleton(jwt);

// ---- AuthN / AuthZ ----------------------------------------------------------------------------
builder.Services.AddAuthentication(JwtBearerDefaults.AuthenticationScheme).AddJwtBearer(o =>
{
    o.TokenValidationParameters = new TokenValidationParameters
    {
        ValidIssuer = jwt.Issuer,
        ValidAudience = jwt.Audience,
        IssuerSigningKey = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(jwt.SigningKey)),
        ClockSkew = TimeSpan.FromSeconds(30),
        NameClaimType = "sub",
        RoleClaimType = "role",
    };
    o.MapInboundClaims = false;
});
builder.Services.AddAuthorization(o =>
{
    o.AddPolicy("Clinician", p => p.RequireRole("clinician", "admin"));
    o.AddPolicy("Researcher", p => p.RequireRole("researcher", "clinician", "admin"));
    o.AddPolicy("Admin", p => p.RequireRole("admin"));
});

// ---- Rate limiting (per user, falling back to IP) ---------------------------------------------
builder.Services.AddRateLimiter(o =>
{
    o.RejectionStatusCode = StatusCodes.Status429TooManyRequests;
    o.GlobalLimiter = PartitionedRateLimiter.Create<HttpContext, string>(ctx =>
        RateLimitPartition.GetFixedWindowLimiter(
            ctx.User.FindFirst("sub")?.Value ?? ctx.Connection.RemoteIpAddress?.ToString() ?? "anon",
            _ => new FixedWindowRateLimiterOptions { PermitLimit = 60, Window = TimeSpan.FromMinutes(1), QueueLimit = 0 }));
});

// ---- Persistence (audit) ----------------------------------------------------------------------
var cs = builder.Configuration.GetConnectionString("Audit") ?? "Data Source=audit.db";
builder.Services.AddDbContext<AuditDbContext>(o =>
{
    if (cs.Contains("Host=", StringComparison.OrdinalIgnoreCase)) o.UseNpgsql(cs); else o.UseSqlite(cs);
});

// ---- Typed client + resilience ----------------------------------------------------------------
builder.Services.AddHttpClient<AiClient>(c =>
{
    c.BaseAddress = new Uri(aiOpts.BaseUrl);
    c.DefaultRequestHeaders.Add("X-Internal-Key", aiOpts.InternalKey);
}).AddStandardResilienceHandler(o =>
{
    // POSTs here are idempotent computations (no side effects), so retrying them is safe.
    o.TotalRequestTimeout.Timeout = TimeSpan.FromSeconds(aiOpts.TimeoutSeconds);
    o.AttemptTimeout.Timeout = TimeSpan.FromSeconds(Math.Max(2, aiOpts.TimeoutSeconds / 2));
    o.Retry.MaxRetryAttempts = 2;
    o.CircuitBreaker.SamplingDuration = TimeSpan.FromSeconds(Math.Max(30, aiOpts.TimeoutSeconds * 2));
});

builder.Services.AddHealthChecks();
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();
builder.Services.Configure<Microsoft.AspNetCore.Http.Json.JsonOptions>(_ => { });

var app = builder.Build();

using (var scope = app.Services.CreateScope())
    scope.ServiceProvider.GetRequiredService<AuditDbContext>().Database.EnsureCreated();

app.UseSwagger();
app.UseSwaggerUI();
app.UseAuthentication();
app.UseRateLimiter();
app.UseAuthorization();
app.UseMiddleware<AuditMiddleware>();

app.MapHealthChecks("/health");

// Relay: forward the AI service's status code and JSON body verbatim (so 422 validation errors reach callers).
static async Task<IResult> Relay(HttpResponseMessage r, CancellationToken ct)
{
    var body = await r.Content.ReadAsStringAsync(ct);
    return Results.Content(body, "application/json", Encoding.UTF8, (int)r.StatusCode);
}

static async Task<IResult> Guard(Func<Task<IResult>> call, ILogger log)
{
    try { return await call(); }
    catch (Exception ex) when (ex is HttpRequestException or TaskCanceledException
                               or Polly.CircuitBreaker.BrokenCircuitException
                               or Polly.Timeout.TimeoutRejectedException)
    {
        log.LogWarning("AI service unavailable: {Type}", ex.GetType().Name); // no payload in logs
        return Results.Problem("AI service temporarily unavailable.", statusCode: 503);
    }
}

var api = app.MapGroup("/api");

api.MapPost("/pgx/diplotype", (HttpContext c, AiClient ai, ILogger<Program> log, CancellationToken ct) =>
    Guard(async () => await Relay(await ai.PostJsonAsync("/v1/pgx/call-diplotype",
        new StreamContent(c.Request.Body) { Headers = { ContentType = new("application/json") } }, ct, c.TraceIdentifier), ct), log))
   .RequireAuthorization("Researcher");

api.MapPost("/predict/clopidogrel-response", (HttpContext c, AiClient ai, ILogger<Program> log, CancellationToken ct) =>
    Guard(async () => await Relay(await ai.PostJsonAsync("/v1/predict/clopidogrel-response",
        new StreamContent(c.Request.Body) { Headers = { ContentType = new("application/json") } }, ct, c.TraceIdentifier), ct), log))
   .RequireAuthorization("Clinician");

api.MapPost("/chat", (HttpContext c, AiClient ai, ILogger<Program> log, CancellationToken ct) =>
    Guard(async () => await Relay(await ai.PostJsonAsync("/v1/chat",
        new StreamContent(c.Request.Body) { Headers = { ContentType = new("application/json") } }, ct, c.TraceIdentifier), ct), log))
   .RequireAuthorization("Researcher");

api.MapPost("/pgx/vcf", (HttpContext c, AiClient ai, ILogger<Program> log, CancellationToken ct) =>
    Guard(async () =>
    {
        if (!c.Request.HasFormContentType) return Results.Problem("multipart/form-data required", statusCode: 415);
        var form = await c.Request.ReadFormAsync(ct);
        var f = form.Files.GetFile("file");
        if (f is null) return Results.Problem("file part required", statusCode: 422);
        if (f.Length > 20 * 1024 * 1024) return Results.Problem("file too large", statusCode: 413);
        using var content = new MultipartFormDataContent();
        await using var s = f.OpenReadStream();
        content.Add(new StreamContent(s), "file", Path.GetFileName(f.FileName));
        return await Relay(await ai.PostJsonAsync("/v1/pgx/from-vcf", content, ct, c.TraceIdentifier), ct);
    }, log)).RequireAuthorization("Clinician").DisableAntiforgery();

api.MapGet("/model", (HttpContext c, AiClient ai, ILogger<Program> log, CancellationToken ct) =>
    Guard(async () => await Relay(await ai.GetAsync("/v1/model", ct, c.TraceIdentifier), ct), log))
   .RequireAuthorization("Researcher");

api.MapGet("/audit", async (AuditDbContext db, [FromQuery] int take = 50) =>
    Results.Ok(await db.Audit.OrderByDescending(a => a.Id).Take(Math.Clamp(take, 1, 500)).ToListAsync()))
   .RequireAuthorization("Admin");

// Development-only token minting so the demo works without an identity provider.
// Production: validate tokens issued by Cognito / Entra ID (set Authority instead of a symmetric key).
if (app.Environment.IsDevelopment() || app.Environment.IsEnvironment("Testing"))
{
    app.MapPost("/dev/token", ([FromBody] DevTokenRequest r, JwtOptions o) =>
    {
        var key = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(o.SigningKey));
        var token = new System.IdentityModel.Tokens.Jwt.JwtSecurityToken(
            o.Issuer, o.Audience,
            [new Claim("sub", r.User), new Claim("role", r.Role)],
            expires: DateTime.UtcNow.AddHours(1),
            signingCredentials: new SigningCredentials(key, SecurityAlgorithms.HmacSha256));
        return Results.Ok(new { access_token = new System.IdentityModel.Tokens.Jwt.JwtSecurityTokenHandler().WriteToken(token) });
    });
}

app.Run();

public sealed record DevTokenRequest(string User, string Role);

public partial class Program;
