namespace Insight.Identity.Api.Contracts;

/// <summary>
/// Specialised RFC 7807 body for <c>422 urn:insight:error:ambiguous_profile</c>.
/// Echoes back the offending lookup and lists the <c>person_id</c>s that
/// matched so the caller can investigate the data-invariant violation
/// without re-querying. Property names serialise via the project-wide
/// <c>JsonNamingPolicy.SnakeCaseLower</c> policy.
/// </summary>
public sealed record AmbiguousProfileProblemResponse(
    string Type,
    string Title,
    int Status,
    string Detail,
    ResolveProfileCommandModel Lookup,
    IReadOnlyList<Guid> PersonIds);
