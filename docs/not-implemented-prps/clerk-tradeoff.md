### Trade-off Analysis: Native SSO (per `SSO-register.md`) vs Clerk.com

This document compares the native, in-repo OAuth/OIDC SSO implementation described in `docs/SSO-register.md` with integrating Clerk.com for user management and SSO.

## Summary Recommendation
- If you need maximum control, on-prem options, fine-grained data governance, and no third‑party runtime dependency, prefer the native SSO approach in `SSO-register.md`.
- If you prioritize time-to-market, enterprise SAML/OIDC support out-of-the-box, and reduced auth/security maintenance, prefer Clerk.

## Side-by-side Comparison

| Dimension | Native SSO (Authlib, RFC 9700) | Clerk.com Integration |
|---|---|---|
| **Time-to-market** | Medium: 2–4 days per provider + testing | Fast: hours to a day with prebuilt widgets |
| **Providers** | Google, GitHub, Microsoft (as in `SSO-register.md`), extendable | Many social IdPs, passkeys, plus Enterprise SAML/OIDC (Okta, Entra ID, Google Workspace, OneLogin, Ping, etc.) |
| **Security controls** | Full control. PKCE, state, nonce, key validation implemented in-app (per `SSO-register.md`) | Clerk manages flows, MFA, device management, bot detection, breach password checks; you verify JWTs via JWKs |
| **Compliance** | Your responsibility (SOC2, GDPR DPIA, data residency) | Clerk provides audited platform; still need app-level DPIA |
| **Vendor lock-in** | Low. Uses standard OAuth/OIDC in codebase | Medium. Data and flows depend on Clerk APIs and claim shapes |
| **Runtime dependency** | None beyond IdPs | Adds Clerk availability and network to auth critical path |
| **Cost** | Engineering time + minimal infra | Platform subscription + overage; reduced eng maintenance |
| **Customization** | Unlimited (you own UX and policy) | High-level UI customizable; deeper flow policy via Clerk config |
| **SSO Enterprise** | Needs separate SAML/OIDC SP implementation | Built-in enterprise connections and SCIM (pro tiers) |
| **Token model** | App issues its own JWTs; consistent with existing `auth_middleware` | Prefer verifying Clerk JWTs server-side; optionally exchange to app JWT for backward-compat |
| **Account linking** | Implemented per `SSO-register.md` (multi-provider, verified-email linking) | Clerk identities model; link multiple IdPs to a Clerk user; you map Clerk user → local `User` |
| **Profile sync** | Your logic (webhooks optional) | Webhooks for user/identity changes; Admin dashboard |
| **Testing** | Full control, local and CI with mocks | Mostly contract tests + local JWT verification using JWKS |

## Architectural Differences

### Native SSO (per `SSO-register.md`)
- Backend hosts `/auth/login/{provider}` and `/auth/callback/{provider}`.
- Uses Authlib, PKCE S256, state/nonce validation, ID token signature verification.
- JIT-provisions `User` records; links by verified email; supports multi-provider linking in `preferences.linked_providers`.
- Issues first-party JWTs via `app/middleware/auth_middleware.py` for session continuity.

Strengths: maximal control, offline capability, no vendor dependency, easier local-first development. Costs: ongoing protocol hardening, new IdP work, enterprise SSO complexity.

### Clerk Integration
- Frontend uses Clerk components/hosted flows; backend treats Clerk as the Identity Provider.
- Protected API requests include Clerk JWT (or session token) in `Authorization: Bearer ...`.
- Backend verifies JWT using Clerk `iss` and JWKs; maps Clerk user → local `User` (JIT create or link using `external_auth_provider='clerk'`, `external_auth_id=<clerk_user_id>`).
- Optionally exchanges a valid Clerk JWT for app JWTs to preserve existing client expectations.

Strengths: dramatically less auth code to maintain, easy enterprise SSO and MFA, dashboard for user admin. Costs: vendor dependency, pricing, some flexibility trade-offs, network dependency during outages.

## Security Considerations
- Native SSO already enforces RFC 9700 controls: PKCE S256, state, nonce, token validation; your team owns patching and audits.
- Clerk: validate `iss`, `aud`, `exp`, `nbf`, `iat`, and signature against Clerk JWKS; optionally enforce `azp`/`org_id` for multi-tenant. Treat Clerk as source-of-truth for email verification.
- For both: never store long-term provider access tokens; prefer ID token/JWT-based auth; keep audit logs for linking events.

## Data Model Impact
- Native: stores `(external_auth_provider, external_auth_id)` per account; optional `linked_providers` array for multi-IdP.
- Clerk: store a single stable `clerk_user_id` as `external_auth_id` with `external_auth_provider='clerk'`; store linked Clerk identities in `preferences.linked_providers` if needed; keep email as primary unique identifier.

## Migration and Coexistence
1. Hybrid mode: accept both app-issued JWTs and Clerk JWTs during transition.
2. Add `POST /api/v1/auth/clerk/exchange` to mint app JWTs from a valid Clerk JWT for legacy clients.
3. Backfill `User.external_auth_provider/id` for existing users on first Clerk login (email match, verified only).
4. Enable Clerk webhooks to keep local profile in sync; do not mutate email automatically without user consent.

## Failure Modes
- Native: IdP outages only affect specific providers; your app can still issue tokens for existing sessions.
- Clerk: Clerk outage affects all auth; mitigate with longer-lived sessions, circuit breakers, and fallbacks where appropriate.

## Cost Outline
- Native: ongoing engineering time (security reviews, provider updates, enterprise SSO work).
- Clerk: recurring subscription; offsets significant maintenance and security work.

## Decision Checklist
Choose Native SSO if:
- You need hard data-sovereignty guarantees or self-hosting of auth.
- Custom flows/policies beyond what hosted IdP platforms allow.

Choose Clerk if:
- You want enterprise SSO, MFA, passkeys quickly and with minimal code.
- Team prefers outsourcing auth/security surface to a specialized provider.


