/**
 * Password rules — declared ONCE, read by every surface that states or enforces them.
 *
 * Two surfaces need this number: the sign-up form (which states it before the
 * submit) and the recovery screen at `/auth/callback` (which states it and
 * enforces it when setting the new password). A literal `6` in each would be
 * two spellings of one rule, free to drift the moment the provider's minimum
 * changes — and the drift would show up as a form that promises one thing and a
 * server that refuses another.
 *
 * This mirrors the auth provider's own minimum. Raising it here is a UI-side
 * tightening only; the provider still enforces its own floor.
 */
export const MIN_PASSWORD_LENGTH = 6;
