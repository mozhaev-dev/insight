using Insight.Identity.Domain.Services;

namespace Insight.Identity.Api.Contracts;

// ── Visibility ──────────────────────────────────────────────────────

public sealed record CreateVisibilityCommandModel(
    Guid ViewerPersonId,
    Guid? ViewedPersonId,
    DateTime? ValidFrom,
    string? Reason);

public sealed record VisibilityResponse(
    Guid VisibilityId,
    Guid InsightTenantId,
    Guid ViewerPersonId,
    Guid? ViewedPersonId,
    DateTime ValidFrom,
    DateTime? ValidTo,
    Guid AuthorPersonId,
    string? Reason,
    DateTime CreatedAt)
{
    public static VisibilityResponse From(Visibility v) => new(
        v.VisibilityId,
        v.InsightTenantId,
        v.ViewerPersonId,
        v.ViewedPersonId,
        v.ValidFrom,
        v.ValidTo,
        v.AuthorPersonId,
        v.Reason,
        v.CreatedAt);
}

// ── Roles ───────────────────────────────────────────────────────────

public sealed record CreateRoleCommandModel(string Name);

public sealed record RoleResponse(Guid RoleId, string Name)
{
    public static RoleResponse From(Role r) => new(r.RoleId, r.Name);
}

// ── Person roles ────────────────────────────────────────────────────

public sealed record CreatePersonRoleCommandModel(
    Guid PersonId,
    Guid RoleId,
    DateTime? ValidFrom,
    string? Reason);

public sealed record PersonRoleResponse(
    Guid PersonRoleId,
    Guid InsightTenantId,
    Guid PersonId,
    Guid RoleId,
    DateTime ValidFrom,
    DateTime? ValidTo,
    Guid AuthorPersonId,
    string? Reason,
    DateTime CreatedAt)
{
    public static PersonRoleResponse From(PersonRole pr) => new(
        pr.PersonRoleId,
        pr.InsightTenantId,
        pr.PersonId,
        pr.RoleId,
        pr.ValidFrom,
        pr.ValidTo,
        pr.AuthorPersonId,
        pr.Reason,
        pr.CreatedAt);
}

// ── Shared ──────────────────────────────────────────────────────────

public sealed record RevokeReasonModel(string? Reason);

public sealed record ListResponse<T>(IReadOnlyList<T> Items, string? NextCursor);
