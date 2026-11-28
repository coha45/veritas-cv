// Initial UI configuration so the controls render before the broker's first
// TOPDOWN snapshot arrives. The broker's traffic_checkers.json remains the
// runtime source of truth and replaces this list when it connects.
export const defaultTrafficCheckers = []
