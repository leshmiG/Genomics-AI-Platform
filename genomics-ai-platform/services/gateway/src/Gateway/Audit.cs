using Microsoft.EntityFrameworkCore;

namespace Gateway;

/// <summary>
/// Audit rows deliberately hold NO request/response bodies: genomic data is identifying and must not
/// leak into logs. Only who, what route, outcome and a correlation id are stored.
/// </summary>
public sealed class AuditEntry
{
    public long Id { get; set; }
    public DateTime TimestampUtc { get; set; }
    public string UserId { get; set; } = "";
    public string Role { get; set; } = "";
    public string Method { get; set; } = "";
    public string Path { get; set; } = "";
    public int StatusCode { get; set; }
    public long DurationMs { get; set; }
    public string RequestId { get; set; } = "";
}

public sealed class AuditDbContext(DbContextOptions<AuditDbContext> options) : DbContext(options)
{
    public DbSet<AuditEntry> Audit => Set<AuditEntry>();

    protected override void OnModelCreating(ModelBuilder b)
    {
        b.Entity<AuditEntry>().HasIndex(a => a.TimestampUtc);
        b.Entity<AuditEntry>().HasIndex(a => a.UserId);
    }
}

public sealed class AuditMiddleware(RequestDelegate next, ILogger<AuditMiddleware> log)
{
    private static readonly string[] Audited = ["/api/"];

    public async Task Invoke(HttpContext ctx, AuditDbContext db)
    {
        if (!Audited.Any(p => ctx.Request.Path.StartsWithSegments(p.TrimEnd('/'))))
        {
            await next(ctx);
            return;
        }
        var sw = System.Diagnostics.Stopwatch.StartNew();
        try { await next(ctx); }
        finally
        {
            sw.Stop();
            try
            {
                db.Audit.Add(new AuditEntry
                {
                    TimestampUtc = DateTime.UtcNow,
                    UserId = ctx.User.FindFirst("sub")?.Value ?? "anonymous",
                    Role = ctx.User.FindFirst("role")?.Value ?? "",
                    Method = ctx.Request.Method,
                    Path = ctx.Request.Path.Value ?? "",
                    StatusCode = ctx.Response.StatusCode,
                    DurationMs = sw.ElapsedMilliseconds,
                    RequestId = ctx.TraceIdentifier,
                });
                await db.SaveChangesAsync();
            }
            catch (Exception ex)
            {
                // An audit failure must be loud; whether to fail the request is a policy decision
                // (see docs/ARCHITECTURE.md). Here we log without the payload and continue.
                log.LogError(ex, "Audit write failed for {RequestId}", ctx.TraceIdentifier);
            }
        }
    }
}
