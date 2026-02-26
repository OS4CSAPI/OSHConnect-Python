# Schema immutability and versioning (CSAPI Part 2)

CSAPI Part 2 requires servers to **reject schema modifications** for:
- a **DataStream** once observations exist, and
- a **ControlStream** once commands exist.

Practical guidance for this scenario pack:

1. Treat each `schema` as a *contract*. Define a maximal schema up-front whenever possible.
2. If you need additional fields later, create a **new** DataStream/ControlStream (new id) rather than changing the existing schema.
3. Keep both streams available to clients during migration, then retire older ones if desired.

This aligns with the Part 2 conformance tests that expect 409-style conflict behavior when attempting schema updates after data exists.
