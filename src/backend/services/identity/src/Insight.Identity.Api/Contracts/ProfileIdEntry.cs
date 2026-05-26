namespace Insight.Identity.Api.Contracts;

/// <summary>
/// One source-native account id bound to a person — last observed
/// (`value_type='id'`, latest per (tenant, person, source_type, source_id)).
/// Property names serialise via the project-wide
/// <c>JsonNamingPolicy.SnakeCaseLower</c> policy.
/// </summary>
public sealed record ProfileIdEntry(
    string InsightSourceType,
    Guid InsightSourceId,
    string Value);
