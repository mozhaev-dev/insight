using System.Security.Claims;
using FluentAssertions;
using Insight.Identity.Api.Auth;
using Microsoft.AspNetCore.Http;
using Xunit;

namespace Insight.Identity.Tests.Unit;

public sealed class JwtTenantContextTests
{
    private const string ClaimName = "insight_tenant_id";
    private static readonly Guid TenantId = Guid.Parse("22222222-2222-2222-2222-222222222222");

    private static DefaultHttpContext ContextWithClaim(string? value)
    {
        var context = new DefaultHttpContext();
        var claims = value is null
            ? Array.Empty<Claim>()
            : new[] { new Claim(ClaimName, value) };
        context.User = new ClaimsPrincipal(new ClaimsIdentity(claims, "test"));
        return context;
    }

    [Fact]
    public void Returns_parsed_guid_when_claim_present()
    {
        var resolved = new JwtTenantContext().Resolve(ContextWithClaim(TenantId.ToString()));

        resolved.Should().Be(TenantId);
    }

    [Fact]
    public void Returns_null_when_claim_missing()
    {
        var resolved = new JwtTenantContext().Resolve(ContextWithClaim(null));

        resolved.Should().BeNull();
    }

    [Theory]
    [InlineData("")]
    [InlineData("not-a-guid")]
    [InlineData("22222222-2222-2222-2222")]
    public void Returns_null_when_claim_is_not_a_guid(string raw)
    {
        var resolved = new JwtTenantContext().Resolve(ContextWithClaim(raw));

        resolved.Should().BeNull();
    }

    [Fact]
    public void Rejects_guid_empty()
    {
        var resolved = new JwtTenantContext().Resolve(ContextWithClaim(Guid.Empty.ToString()));

        // Guid.Empty is parseable but is not a real identity — accepting it
        // would let a JWT with a default-valued claim pin a phantom tenant
        // context for every downstream lookup.
        resolved.Should().BeNull();
    }
}
