/**
 * mandatepatch - reference implementation of the artifact layer described in
 * Technical Disclosure Commons #11517, "Mandate Lifecycle Extensions for Agentic
 * Payment Credentials" (Matt Kirby, CC-BY).
 *
 * The artifact layer ships first. This package defines the objects and their
 * canonical form. It deliberately implements no semantic scorer, no service, and
 * no policy engine.
 */

export * from "./types";
export * from "./canonicalize";
