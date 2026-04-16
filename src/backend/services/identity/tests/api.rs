//! HTTP integration tests for the Identity Resolution stub.

use axum::http::{Request, StatusCode};
use http_body_util::BodyExt;
use identity_resolution::people::PeopleStore;
use tower::ServiceExt;

fn test_data() -> &'static [u8] {
    br#"{"id":"1","status":"Active","firstName":"Alice","lastName":"Smith","displayName":"Alice Smith","workEmail":"alice@example.com","department":"Engineering","division":"R&D","jobTitle":"Staff Engineer","supervisorEmail":"bob@example.com","supervisor":"Jones, Bob"}
{"id":"2","status":"Active","firstName":"Bob","lastName":"Jones","displayName":"Bob Jones","workEmail":"bob@example.com","department":"Engineering","division":"R&D","jobTitle":"Engineering Manager","supervisorEmail":null,"supervisor":null}
{"id":"3","status":"Active","firstName":"Dave","lastName":"Ng","displayName":"Dave Ng","workEmail":"dave@example.com","department":"Engineering","division":"R&D","jobTitle":"Senior Engineer","supervisorEmail":"bob@example.com","supervisor":"Jones, Bob"}"#
}

fn app() -> axum::Router {
    let store = PeopleStore::from_json_lines(test_data()).expect("test data");
    identity_resolution::build_router(store)
}

async fn get(uri: &str) -> (StatusCode, serde_json::Value) {
    let resp = app()
        .oneshot(Request::get(uri).body(axum::body::Body::empty()).expect("request"))
        .await
        .expect("response");
    let status = resp.status();
    let body = resp.into_body().collect().await.expect("body").to_bytes();
    let json: serde_json::Value = serde_json::from_slice(&body).unwrap_or(serde_json::Value::Null);
    (status, json)
}

#[tokio::test]
async fn health_returns_healthy() {
    let (status, body) = get("/health").await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["status"], "healthy");
}

#[tokio::test]
async fn healthz_returns_ok() {
    let resp = app()
        .oneshot(Request::get("/healthz").body(axum::body::Body::empty()).expect("request"))
        .await
        .expect("response");
    assert_eq!(resp.status(), StatusCode::OK);
    let body = resp.into_body().collect().await.expect("body").to_bytes();
    assert_eq!(&body[..], b"ok");
}

#[tokio::test]
async fn get_person_returns_data() {
    let (status, body) = get("/v1/persons/alice@example.com").await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["email"], "alice@example.com");
    assert_eq!(body["display_name"], "Alice Smith");
    assert_eq!(body["department"], "Engineering");
    assert_eq!(body["job_title"], "Staff Engineer");
    assert_eq!(body["supervisor_email"], "bob@example.com");
}

#[tokio::test]
async fn get_person_case_insensitive() {
    let (status, body) = get("/v1/persons/Alice@Example.COM").await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["email"], "alice@example.com");
}

#[tokio::test]
async fn get_person_not_found() {
    let (status, body) = get("/v1/persons/nobody@example.com").await;
    assert_eq!(status, StatusCode::NOT_FOUND);
    assert_eq!(body["status"], 404);
    assert!(body["detail"].as_str().expect("detail").contains("nobody@example.com"));
}

#[tokio::test]
async fn supervisor_includes_subordinates() {
    let (status, body) = get("/v1/persons/bob@example.com").await;
    assert_eq!(status, StatusCode::OK);

    let subs = body["subordinates"].as_array().expect("subordinates array");
    assert_eq!(subs.len(), 2);

    let emails: Vec<&str> = subs.iter().map(|s| s["email"].as_str().expect("email")).collect();
    assert!(emails.contains(&"alice@example.com"));
    assert!(emails.contains(&"dave@example.com"));
}

#[tokio::test]
async fn leaf_has_no_subordinates() {
    let (status, body) = get("/v1/persons/alice@example.com").await;
    assert_eq!(status, StatusCode::OK);
    let subs = body["subordinates"].as_array().expect("subordinates array");
    assert!(subs.is_empty());
}
