namespace Insight.Identity.Api.Contracts;

/// <summary>
/// RFC 7807 problem-details body. Field shape matches the Rust stub for
/// consumer compatibility (<c>type</c>, <c>title</c>, <c>status</c>,
/// <c>detail</c>). Property names serialise via the project-wide
/// <c>JsonNamingPolicy.SnakeCaseLower</c> policy.
/// </summary>
public sealed record ProblemResponse(
    string Type,
    string Title,
    int Status,
    string Detail);
