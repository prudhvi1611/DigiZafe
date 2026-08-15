# Ethics Policy — Amber Discovery

## User autonomy

Amber scans are never silently enabled. The user must see:

- the layer name;
- the destination purpose;
- the type of data sent;
- the limitations;
- the fact that results may be historical or incomplete.

## Data minimization

DigiZafe stores:

- source;
- layer;
- timestamp;
- redacted metadata;
- stable reference;
- attribution;
- confidence.

DigiZafe does not require or retain:

- full breach dumps;
- full archived page bodies;
- illicit marketplace content;
- credential material;
- raw HTML indefinitely.

## Self-only safety

Every Amber scan requires:

- authenticated user;
- verified identifier;
- user-scoped RLS;
- explicit Amber consent;
- audit event;
- egress ledger entry.

## Constrained-Dark boundary

Constrained-Dark is limited to an operator-approved public index over HTTPS.
It is not a Tor client and is not a marketplace crawler.

## Uncertainty language

Amber findings should be described as:

- historical;
- indexed;
- possible;
- metadata-only;
- requiring confirmation.

They should not be presented as definitive proof of current criminal exposure.
