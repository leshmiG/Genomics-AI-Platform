using System.Net.Http.Headers;

namespace Gateway;

/// <summary>Typed HttpClient to the Python AI service. Resilience (retry, circuit breaker, timeouts)
/// is attached in Program.cs via AddStandardResilienceHandler.</summary>
public sealed class AiClient(HttpClient http)
{
    public Task<HttpResponseMessage> PostJsonAsync(string path, HttpContent body, CancellationToken ct, string? requestId = null)
        => Send(HttpMethod.Post, path, body, requestId, ct);

    public Task<HttpResponseMessage> GetAsync(string path, CancellationToken ct, string? requestId = null)
        => Send(HttpMethod.Get, path, null, requestId, ct);

    private Task<HttpResponseMessage> Send(HttpMethod m, string path, HttpContent? body, string? requestId, CancellationToken ct)
    {
        var req = new HttpRequestMessage(m, path) { Content = body };
        if (!string.IsNullOrEmpty(requestId)) req.Headers.TryAddWithoutValidation("X-Request-ID", requestId);
        return http.SendAsync(req, HttpCompletionOption.ResponseHeadersRead, ct);
    }
}
