using FluentAssertions;
using Insight.Identity.Api.Auth;
using Microsoft.AspNetCore.Http;
using Xunit;

namespace Insight.Identity.Tests.Unit;

public sealed class HeaderTenantContextTests
{
    private static readonly Guid TenantId = Guid.Parse("11111111-1111-1111-1111-111111111111");

    [Fact]
    public void Returns_parsed_guid_when_header_present()
    {
        var context = new DefaultHttpContext();
        context.Request.Headers[HeaderTenantContext.HeaderName] = TenantId.ToString();

        var resolved = new HeaderTenantContext().Resolve(context);

        resolved.Should().Be(TenantId);
    }

    [Fact]
    public void Returns_null_when_header_missing()
    {
        var context = new DefaultHttpContext();

        var resolved = new HeaderTenantContext().Resolve(context);

        resolved.Should().BeNull();
    }

    [Theory]
    [InlineData("")]
    [InlineData("not-a-guid")]
    [InlineData("11111111-1111-1111-1111")]
    public void Returns_null_when_header_value_is_not_a_guid(string raw)
    {
        var context = new DefaultHttpContext();
        context.Request.Headers[HeaderTenantContext.HeaderName] = raw;

        var resolved = new HeaderTenantContext().Resolve(context);

        resolved.Should().BeNull();
    }

    [Fact]
    public void Rejects_guid_empty()
    {
        var context = new DefaultHttpContext();
        context.Request.Headers[HeaderTenantContext.HeaderName] = Guid.Empty.ToString();

        var resolved = new HeaderTenantContext().Resolve(context);

        // Guid.Empty is parseable but is not a real identity — accepting it
        // would let a misbehaving gateway pin a phantom tenant context for
        // every downstream lookup.
        resolved.Should().BeNull();
    }
}
