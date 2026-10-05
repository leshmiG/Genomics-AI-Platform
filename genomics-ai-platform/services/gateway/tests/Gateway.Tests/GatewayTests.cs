using System.Net;
using System.Net.Http.Json;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.Extensions.DependencyInjection;

namespace Gateway.Tests;

/// <summary>Replaces the AI service with a stub so tests need no Python process.</summary>
public sealed class StubHandler(HttpStatusCode code, string body) : HttpMessageHandler
{
    public HttpRequestMessage? Last;
    protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage r, CancellationToken ct)
    {
        Last = r;
        return Task.FromResult(new HttpResponseMessage(code) { Content = new StringContent(body, System.Text.Encoding.UTF8, "application/json") });
    }
}

public sealed class Factory(StubHandler stub) : WebApplicationFactory<Program>
{
    protected override void ConfigureWebHost(IWebHostBuilder b)
    {
        b.UseEnvironment("Testing");
        b.UseSetting("ConnectionStrings:Audit", $"Data Source={Path.Combine(Path.GetTempPath(), Guid.NewGuid().ToString("N") + ".db")}");
        b.ConfigureServices(s =>
            s.AddHttpClient<AiClient>().ConfigurePrimaryHttpMessageHandler(() => stub));
    }
}

public class GatewayTests
{
    private static async Task<HttpClient> ClientAs(Factory f, string role)
    {
        var c = f.CreateClient();
        var t = await (await c.PostAsJsonAsync("/dev/token", new { user = "u1", role })).Content.ReadFromJsonAsync<Dictionary<string, string>>();
        c.DefaultRequestHeaders.Authorization = new("Bearer", t!["access_token"]);
        return c;
    }

    [Fact]
    public async Task Health_is_open()
    {
        using var f = new Factory(new StubHandler(HttpStatusCode.OK, "{}"));
        Assert.Equal(HttpStatusCode.OK, (await f.CreateClient().GetAsync("/health")).StatusCode);
    }

    [Fact]
    public async Task Api_requires_token()
    {
        using var f = new Factory(new StubHandler(HttpStatusCode.OK, "{}"));
        var r = await f.CreateClient().PostAsJsonAsync("/api/chat", new { message = "hi" });
        Assert.Equal(HttpStatusCode.Unauthorized, r.StatusCode);
    }

    [Fact]
    public async Task Researcher_cannot_call_clinician_endpoint()
    {
        using var f = new Factory(new StubHandler(HttpStatusCode.OK, "{}"));
        var c = await ClientAs(f, "researcher");
        var r = await c.PostAsJsonAsync("/api/predict/clopidogrel-response", new { });
        Assert.Equal(HttpStatusCode.Forbidden, r.StatusCode);
    }

    [Fact]
    public async Task Relays_upstream_status_and_body_and_forwards_request_id()
    {
        var stub = new StubHandler(HttpStatusCode.UnprocessableEntity, "{\"detail\":\"bad\"}");
        using var f = new Factory(stub);
        var c = await ClientAs(f, "clinician");
        var r = await c.PostAsJsonAsync("/api/pgx/diplotype", new { gene = "CYP2C19", diplotype = "2/2" });
        Assert.Equal(HttpStatusCode.UnprocessableEntity, r.StatusCode);
        Assert.Contains("bad", await r.Content.ReadAsStringAsync());
        Assert.True(stub.Last!.Headers.Contains("X-Request-ID"));
    }

    [Fact]
    public async Task Audit_records_calls_without_bodies_and_is_admin_only()
    {
        using var f = new Factory(new StubHandler(HttpStatusCode.OK, "{}"));
        var clin = await ClientAs(f, "clinician");
        await clin.PostAsJsonAsync("/api/chat", new { message = "secret-ish text" });
        Assert.Equal(HttpStatusCode.Forbidden, (await clin.GetAsync("/api/audit")).StatusCode);

        var admin = await ClientAs(f, "admin");
        var text = await (await admin.GetAsync("/api/audit")).Content.ReadAsStringAsync();
        Assert.Contains("/api/chat", text);
        Assert.DoesNotContain("secret-ish", text);
    }
}
