namespace Insight.Identity.Domain.Services;

/// <summary>
/// Pagination request for list-endpoint readers. Today only
/// <see cref="Limit"/> is wired; <see cref="Cursor"/> exists as a
/// forward-compatible field so the response shape (<see cref="PagedResult{T}"/>)
/// can grow into cursor-based paging without breaking callers.
/// </summary>
public sealed record PageRequest(int Limit, string? Cursor = null)
{
    public const int DefaultLimit = 50;
    public const int MaxLimit = 500;

    public static PageRequest Default => new(DefaultLimit);

    public PageRequest WithClampedLimit() =>
        this with { Limit = Math.Clamp(Limit, 1, MaxLimit) };
}

/// <summary>One page of items plus the cursor to fetch the next page.</summary>
public sealed record PagedResult<T>(IReadOnlyList<T> Items, string? NextCursor);

/// <summary>Sort directive — <see cref="Column"/> is a server-whitelisted name.</summary>
public sealed record SortRequest(string Column, SortDirection Direction = SortDirection.Ascending);

public enum SortDirection
{
    Ascending,
    Descending,
}
