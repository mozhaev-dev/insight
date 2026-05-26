namespace Insight.Identity.Api.Contracts;

/// <summary>
/// Body of <c>POST /v1/profiles</c>. Two valid shapes selected by
/// <see cref="ValueType"/>:
/// <list type="bullet">
///   <item>
///     <c>value_type="email"</c> — match across all sources for the tenant.
///     <c>insight_source_type</c> and <c>insight_source_id</c> MUST be null.
///   </item>
///   <item>
///     <c>value_type="id"</c> — match a source-native account id within one
///     source instance. Both <c>insight_source_type</c> and
///     <c>insight_source_id</c> MUST be supplied.
///   </item>
/// </list>
/// The handler resolves to exactly one <c>person_id</c>; multiple matches
/// surface as <c>422 urn:insight:error:ambiguous_profile</c>. Property
/// names serialise via the project-wide <c>JsonNamingPolicy.SnakeCaseLower</c>
/// policy.
/// </summary>
public sealed record ResolveProfileCommandModel(
    string? ValueType,
    string? Value,
    string? InsightSourceType,
    Guid? InsightSourceId);
