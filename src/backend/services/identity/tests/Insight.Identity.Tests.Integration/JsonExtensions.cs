using System.Net.Http.Json;
using System.Text.Json;

namespace Insight.Identity.Tests.Integration;

/// <summary>
/// Single source of truth for the JSON wire-format used by the identity
/// service over HTTP. Mirrors the server-side configuration in
/// <c>Program.cs</c> (<c>JsonNamingPolicy.SnakeCaseLower</c>) so tests
/// serialise request bodies and deserialise responses with the SAME
/// naming policy the server applies.
///
/// Tests MUST go through <see cref="PostJsonAsync"/> / <see cref="ReadJsonAsync"/>
/// instead of the stock <c>PostAsJsonAsync</c> / <c>ReadFromJsonAsync</c>.
/// Forgetting to use these helpers (or deleting this class) breaks every
/// integration test that touches a JSON endpoint at once — wire-format
/// drift between server and tests becomes a build/test failure instead of
/// a silent green pass.
/// </summary>
internal static class JsonExtensions
{
    public static readonly JsonSerializerOptions ApiJsonOptions = new(JsonSerializerDefaults.Web)
    {
        PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
        DictionaryKeyPolicy  = JsonNamingPolicy.SnakeCaseLower,
    };

    public static Task<HttpResponseMessage> PostJsonAsync<T>(
        this HttpClient client,
        string requestUri,
        T body,
        CancellationToken cancellationToken = default) =>
        client.PostAsJsonAsync(requestUri, body, ApiJsonOptions, cancellationToken);

    public static Task<HttpResponseMessage> PostJsonAsync<T>(
        this HttpClient client,
        Uri requestUri,
        T body,
        CancellationToken cancellationToken = default) =>
        client.PostAsJsonAsync(requestUri, body, ApiJsonOptions, cancellationToken);

    public static Task<T?> ReadJsonAsync<T>(
        this HttpResponseMessage response,
        CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(response);
        return response.Content.ReadFromJsonAsync<T>(ApiJsonOptions, cancellationToken);
    }
}
