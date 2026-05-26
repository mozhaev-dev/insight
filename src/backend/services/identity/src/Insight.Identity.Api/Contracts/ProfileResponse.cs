using System.Text.Json.Serialization;
using Insight.Identity.Domain;

namespace Insight.Identity.Api.Contracts;

/// <summary>
/// Response body of <c>POST /v1/profiles</c>. Extends
/// <see cref="PersonResponse"/> with profile-specific fields
/// (<see cref="InsightTenantId"/>, <see cref="Username"/>,
/// <see cref="EmployeeId"/>, and <see cref="Ids"/> — every current
/// <c>value_type='id'</c> observation, one per (source_type,
/// source_id) instance). Null-valued optional fields are omitted
/// from JSON to keep the payload tight. Property names are
/// serialised in snake_case via the project-wide
/// <c>JsonNamingPolicy.SnakeCaseLower</c> policy configured in
/// <c>Program.cs</c>; the only attributes here are the
/// <see cref="JsonIgnoreAttribute"/> directives that control the
/// null-write behaviour.
/// </summary>
public sealed record ProfileResponse(
    Guid PersonId,
    Guid InsightTenantId,
    string? Email,
    string? DisplayName,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] string? FirstName,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] string? LastName,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] string? Department,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] string? Division,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] string? JobTitle,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] string? Status,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] string? Username,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] string? EmployeeId,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] string? SupervisorEmail,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] string? SupervisorName,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] string? ParentEmail,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] string? ParentId,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] Guid? ParentPersonId,
    IReadOnlyList<PersonResponse> Subordinates,
    IReadOnlyList<ProfileIdEntry> Ids)
{
    public static ProfileResponse From(Profile profile)
    {
        ArgumentNullException.ThrowIfNull(profile);
        var ids = profile.Ids.Count == 0
            ? Array.Empty<ProfileIdEntry>()
            : profile.Ids
                .Select(static s => new ProfileIdEntry(s.InsightSourceType, s.InsightSourceId, s.Value))
                .ToArray();
        var subs = profile.Subordinates.Count == 0
            ? Array.Empty<PersonResponse>()
            : profile.Subordinates.Select(PersonResponse.From).ToArray();
        return new ProfileResponse(
            profile.PersonId,
            profile.InsightTenantId,
            profile.Email,
            profile.DisplayName,
            profile.FirstName,
            profile.LastName,
            profile.Department,
            profile.Division,
            profile.JobTitle,
            profile.Status,
            profile.Username,
            profile.EmployeeId,
            profile.SupervisorEmail,
            profile.SupervisorName,
            profile.ParentEmail,
            profile.ParentId,
            profile.ParentPersonId,
            subs,
            ids);
    }
}
