using Insight.Identity.Domain;

namespace Insight.Identity.Api.Contracts;

/// <summary>
/// Wire-format projection of <see cref="Person"/> returned by
/// <c>GET /v1/persons/{email}</c>. Property names are serialised in
/// snake_case via the project-wide <c>JsonNamingPolicy.SnakeCaseLower</c>
/// policy configured in <c>Program.cs</c>; no per-property attributes
/// needed here.
/// </summary>
public sealed record PersonResponse(
    Guid PersonId,
    string Email,
    string DisplayName,
    string FirstName,
    string LastName,
    string Department,
    string Division,
    string JobTitle,
    string Status,
    string? SupervisorEmail,
    string? SupervisorName,
    string? ParentEmail,
    string? ParentId,
    Guid? ParentPersonId,
    IReadOnlyList<PersonResponse> Subordinates)
{
    public static PersonResponse From(Person person)
    {
        ArgumentNullException.ThrowIfNull(person);
        var subs = person.Subordinates.Count == 0
            ? Array.Empty<PersonResponse>()
            : person.Subordinates.Select(From).ToArray();
        return new PersonResponse(
            person.PersonId,
            person.Email,
            person.DisplayName,
            person.FirstName,
            person.LastName,
            person.Department,
            person.Division,
            person.JobTitle,
            person.Status,
            person.SupervisorEmail,
            person.SupervisorName,
            person.ParentEmail,
            person.ParentId,
            person.ParentPersonId,
            subs);
    }
}
