namespace Gateway;

public sealed class AiServiceOptions
{
    public string BaseUrl { get; set; } = "http://localhost:8000";
    public string InternalKey { get; set; } = "dev-internal-key";
    public int TimeoutSeconds { get; set; } = 20;
}

public sealed class JwtOptions
{
    public string Issuer { get; set; } = "genomics-gateway";
    public string Audience { get; set; } = "genomics-clients";
    /// <summary>HS256 signing key. Must be >= 32 chars. Override via env Jwt__SigningKey / Secrets Manager.</summary>
    public string SigningKey { get; set; } = "dev-only-signing-key-change-me-0123456789";
}
