// Generic date validation. All parameters come from the provider config.

const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;

// Returns the most recent date that should be queryable (today − lagDays).
function upperBoundDate(lagDays) {
  const d = new Date();
  d.setUTCDate(d.getUTCDate() - lagDays);
  return d.toISOString().slice(0, 10);
}

// Validates a single YYYY-MM-DD date against the provider's constraints.
// Returns null on success, or an error string.
function validateDate(value, { minDate, lagDays }, label = 'date') {
  if (!value) return `${label} is required`;
  if (!DATE_RE.test(value)) return `${label} must be YYYY-MM-DD`;
  if (minDate && value < minDate) {
    return `${label} is before the minimum queryable date (${minDate})`;
  }
  if (lagDays != null) {
    const ub = upperBoundDate(lagDays);
    if (value > ub) {
      return `${label} is within the ${lagDays}-day reporting lag window (latest queryable: ${ub})`;
    }
  }
  return null;
}

function dayDiff(fromDateStr, toDateStr) {
  const ms = new Date(toDateStr) - new Date(fromDateStr);
  return Math.round(ms / (1000 * 60 * 60 * 24));
}

// Validates a date range for an endpoint with dateRange config.
// opts = { startParam, endParam, maxDays?, exclusiveEnd? }
function validateDateRange(startValue, endValue, constraints, opts) {
  const startErr = validateDate(startValue, constraints, opts.startParam);
  if (startErr) return startErr;

  if (endValue) {
    const endErr = validateDate(endValue, constraints, opts.endParam);
    if (endErr) return endErr;

    if (opts.exclusiveEnd && endValue <= startValue) {
      return `${opts.endParam} must be after ${opts.startParam} (exclusive)`;
    }
    if (!opts.exclusiveEnd && endValue < startValue) {
      return `${opts.endParam} must be >= ${opts.startParam}`;
    }
    if (opts.maxDays) {
      const diff = dayDiff(startValue, endValue);
      if (diff > opts.maxDays) {
        return `Date range exceeds ${opts.maxDays} days — split into smaller windows`;
      }
    }
  }
  return null;
}

module.exports = { validateDate, validateDateRange, upperBoundDate, dayDiff };
