//! In-memory people store built from `bronze_bamboohr.employees`.
//!
//! Loaded once at startup. Builds email→person lookup and
//! supervisor→subordinates relationships.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// Raw row from `bronze_bamboohr.employees`.
#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct RawEmployee {
    id: String,
    #[serde(default)]
    status: Option<String>,
    #[serde(default)]
    first_name: Option<String>,
    #[serde(default)]
    last_name: Option<String>,
    #[serde(default)]
    display_name: Option<String>,
    #[serde(default)]
    work_email: Option<String>,
    #[serde(default)]
    department: Option<String>,
    #[serde(default)]
    division: Option<String>,
    #[serde(default)]
    job_title: Option<String>,
    #[serde(default)]
    supervisor_email: Option<String>,
    #[serde(default)]
    supervisor: Option<String>,
}

/// Person returned by the API.
#[derive(Debug, Clone, Serialize)]
pub struct Person {
    pub email: String,
    pub display_name: String,
    pub first_name: String,
    pub last_name: String,
    pub department: String,
    pub division: String,
    pub job_title: String,
    pub status: String,
    pub supervisor_email: Option<String>,
    pub supervisor_name: Option<String>,
    pub subordinates: Vec<Subordinate>,
}

/// Subordinate summary.
#[derive(Debug, Clone, Serialize)]
pub struct Subordinate {
    pub email: String,
    pub display_name: String,
    pub job_title: String,
}

/// In-memory store: email (lowercased) → Person.
pub struct PeopleStore {
    by_email: HashMap<String, Person>,
    aliases: HashMap<String, String>,
}

impl PeopleStore {
    /// Load all active employees from ClickHouse, deduplicate by id
    /// (keep latest by `_airbyte_extracted_at`), and build relationships.
    pub async fn load(ch: &insight_clickhouse::Client) -> anyhow::Result<Self> {
        tracing::info!("loading people from bronze_bamboohr.employees");

        let sql = r"
            SELECT
                id,
                status,
                firstName,
                lastName,
                displayName,
                workEmail,
                department,
                division,
                jobTitle,
                supervisorEmail,
                supervisor
            FROM bronze_bamboohr.employees
            WHERE status = 'Active' AND workEmail != ''
            ORDER BY id, _airbyte_extracted_at DESC
        ";

        let mut cursor = ch.query(sql).fetch_bytes("JSONEachRow").map_err(|e| {
            anyhow::anyhow!("ClickHouse query failed: {e}")
        })?;

        let raw_bytes = cursor.collect().await.map_err(|e| {
            anyhow::anyhow!("ClickHouse fetch failed: {e}")
        })?;

        // Parse rows, deduplicate by id (first row per id wins due to ORDER BY)
        let mut seen_ids: HashMap<String, ()> = HashMap::new();
        let mut employees: Vec<RawEmployee> = Vec::new();

        if !raw_bytes.is_empty() {
            for line in raw_bytes.split(|&b| b == b'\n').filter(|l| !l.is_empty()) {
                let row: RawEmployee = serde_json::from_slice(line)?;
                if seen_ids.contains_key(&row.id) {
                    continue;
                }
                seen_ids.insert(row.id.clone(), ());
                employees.push(row);
            }
        }

        tracing::info!(count = employees.len(), "parsed unique active employees");

        Ok(Self::build(employees))
    }

    /// Build a store from raw JSON lines (one `RawEmployee` per line).
    /// Used for testing without ClickHouse.
    pub fn from_json_lines(data: &[u8]) -> anyhow::Result<Self> {
        let mut seen_ids: HashMap<String, ()> = HashMap::new();
        let mut employees: Vec<RawEmployee> = Vec::new();

        for line in data.split(|&b| b == b'\n').filter(|l| !l.is_empty()) {
            let row: RawEmployee = serde_json::from_slice(line)?;
            if seen_ids.contains_key(&row.id) {
                continue;
            }
            seen_ids.insert(row.id.clone(), ());
            employees.push(row);
        }

        let mut store = Self::build(employees);
        store.aliases = HashMap::new(); // no aliases in test mode
        Ok(store)
    }

    fn build(employees: Vec<RawEmployee>) -> Self {
        let mut by_email: HashMap<String, Person> = HashMap::new();
        for emp in &employees {
            let email = emp.work_email.as_deref().unwrap_or_default();
            if email.is_empty() {
                continue;
            }
            let key = email.to_lowercase();
            by_email.insert(key, Person {
                email: email.to_owned(),
                display_name: emp.display_name.clone().unwrap_or_default(),
                first_name: emp.first_name.clone().unwrap_or_default(),
                last_name: emp.last_name.clone().unwrap_or_default(),
                department: emp.department.clone().unwrap_or_default(),
                division: emp.division.clone().unwrap_or_default(),
                job_title: emp.job_title.clone().unwrap_or_default(),
                status: emp.status.clone().unwrap_or_default(),
                supervisor_email: emp.supervisor_email.clone(),
                supervisor_name: emp.supervisor.clone(),
                subordinates: Vec::new(),
            });
        }

        let mut subordinate_map: HashMap<String, Vec<Subordinate>> = HashMap::new();
        for emp in &employees {
            if let Some(ref sup_email) = emp.supervisor_email {
                let sup_key = sup_email.to_lowercase();
                let email = emp.work_email.as_deref().unwrap_or_default();
                if email.is_empty() {
                    continue;
                }
                subordinate_map.entry(sup_key).or_default().push(Subordinate {
                    email: email.to_owned(),
                    display_name: emp.display_name.clone().unwrap_or_default(),
                    job_title: emp.job_title.clone().unwrap_or_default(),
                });
            }
        }

        for (email_key, person) in &mut by_email {
            if let Some(subs) = subordinate_map.remove(email_key) {
                person.subordinates = subs;
            }
        }

        // MVP: hardcoded email aliases for test accounts
        let mut aliases = HashMap::new();
        aliases.insert(
            "test@vz.com".to_owned(),
            "oleksii.shponarskyi@virtuozzo.com".to_owned(),
        );

        Self { by_email, aliases }
    }

    pub fn get_by_email(&self, email: &str) -> Option<&Person> {
        let key = email.to_lowercase();
        // Check aliases first, then direct lookup
        let resolved = self.aliases.get(&key).unwrap_or(&key);
        self.by_email.get(resolved)
    }

    pub fn len(&self) -> usize {
        self.by_email.len()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn test_data() -> &'static [u8] {
        br#"{"id":"1","status":"Active","firstName":"Alice","lastName":"Smith","displayName":"Alice Smith","workEmail":"alice@example.com","department":"Engineering","division":"R&D","jobTitle":"Staff Engineer","supervisorEmail":"bob@example.com","supervisor":"Smith, Bob"}
{"id":"2","status":"Active","firstName":"Bob","lastName":"Jones","displayName":"Bob Jones","workEmail":"bob@example.com","department":"Engineering","division":"R&D","jobTitle":"Engineering Manager","supervisorEmail":"carol@example.com","supervisor":"Lee, Carol"}
{"id":"3","status":"Active","firstName":"Carol","lastName":"Lee","displayName":"Carol Lee","workEmail":"carol@example.com","department":"Engineering","division":"R&D","jobTitle":"VP Engineering","supervisorEmail":null,"supervisor":null}
{"id":"4","status":"Active","firstName":"Dave","lastName":"Ng","displayName":"Dave Ng","workEmail":"dave@example.com","department":"Engineering","division":"R&D","jobTitle":"Senior Engineer","supervisorEmail":"bob@example.com","supervisor":"Jones, Bob"}"#
    }

    #[test]
    fn loads_all_employees() {
        let store = PeopleStore::from_json_lines(test_data()).unwrap();
        assert_eq!(store.len(), 4);
    }

    #[test]
    fn lookup_by_email() {
        let store = PeopleStore::from_json_lines(test_data()).unwrap();
        let alice = store.get_by_email("alice@example.com").unwrap();
        assert_eq!(alice.display_name, "Alice Smith");
        assert_eq!(alice.department, "Engineering");
        assert_eq!(alice.job_title, "Staff Engineer");
    }

    #[test]
    fn lookup_case_insensitive() {
        let store = PeopleStore::from_json_lines(test_data()).unwrap();
        assert!(store.get_by_email("Alice@Example.COM").is_some());
    }

    #[test]
    fn lookup_not_found() {
        let store = PeopleStore::from_json_lines(test_data()).unwrap();
        assert!(store.get_by_email("nobody@example.com").is_none());
    }

    #[test]
    fn supervisor_has_subordinates() {
        let store = PeopleStore::from_json_lines(test_data()).unwrap();
        let bob = store.get_by_email("bob@example.com").unwrap();
        assert_eq!(bob.subordinates.len(), 2);

        let sub_emails: Vec<&str> = bob.subordinates.iter().map(|s| s.email.as_str()).collect();
        assert!(sub_emails.contains(&"alice@example.com"));
        assert!(sub_emails.contains(&"dave@example.com"));
    }

    #[test]
    fn leaf_employee_has_no_subordinates() {
        let store = PeopleStore::from_json_lines(test_data()).unwrap();
        let alice = store.get_by_email("alice@example.com").unwrap();
        assert!(alice.subordinates.is_empty());
    }

    #[test]
    fn supervisor_info_populated() {
        let store = PeopleStore::from_json_lines(test_data()).unwrap();
        let alice = store.get_by_email("alice@example.com").unwrap();
        assert_eq!(alice.supervisor_email.as_deref(), Some("bob@example.com"));
        assert_eq!(alice.supervisor_name.as_deref(), Some("Smith, Bob"));
    }

    #[test]
    fn top_level_has_no_supervisor() {
        let store = PeopleStore::from_json_lines(test_data()).unwrap();
        let carol = store.get_by_email("carol@example.com").unwrap();
        assert!(carol.supervisor_email.is_none());
        assert!(carol.supervisor_name.is_none());
    }

    #[test]
    fn deduplicates_by_id() {
        let data = br#"{"id":"1","status":"Active","firstName":"Alice","lastName":"Smith","displayName":"Alice Smith","workEmail":"alice@example.com","department":"Eng","division":"R&D","jobTitle":"Engineer","supervisorEmail":null,"supervisor":null}
{"id":"1","status":"Active","firstName":"Alice","lastName":"Smith-Updated","displayName":"Alice Smith-Updated","workEmail":"alice@example.com","department":"Eng","division":"R&D","jobTitle":"Staff Engineer","supervisorEmail":null,"supervisor":null}"#;
        let store = PeopleStore::from_json_lines(data).unwrap();
        assert_eq!(store.len(), 1);
        // First row wins (simulating ORDER BY _airbyte_extracted_at DESC)
        let alice = store.get_by_email("alice@example.com").unwrap();
        assert_eq!(alice.last_name, "Smith");
    }

    #[test]
    fn empty_data() {
        let store = PeopleStore::from_json_lines(b"").unwrap();
        assert_eq!(store.len(), 0);
    }

    #[test]
    fn skips_empty_email() {
        let data = br#"{"id":"1","status":"Active","firstName":"Ghost","lastName":"User","displayName":"Ghost","workEmail":"","department":"Eng","division":"R&D","jobTitle":"","supervisorEmail":null,"supervisor":null}"#;
        let store = PeopleStore::from_json_lines(data).unwrap();
        assert_eq!(store.len(), 0);
    }
}
