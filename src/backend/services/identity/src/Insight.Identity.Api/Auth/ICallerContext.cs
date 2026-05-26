using Microsoft.AspNetCore.Http;

namespace Insight.Identity.Api.Auth;

/// <summary>
/// Resolves the calling person for the current HTTP request. Endpoints
/// that need to know "who is asking?" — e.g. visibility filtering,
/// admin-role authz, audit columns on writes — depend on this port.
/// </summary>
public interface ICallerContext
{
    /// <summary>
    /// Returns the caller's <c>person_id</c> for the current request,
    /// or <c>null</c> when the request carries no caller identity
    /// (caller must respond 401 when an identified caller is required).
    /// </summary>
    Guid? Resolve(HttpContext context);
}
