# Canonical Contract Inventory

This document defines the authoritative locations for all domain models and contracts in DigiZafe to prevent duplication and ensure consistency across the codebase.

## 1. Domain Enums and Identifiers

- **Exposure Layers (`ExposureLayer`)**
  - **Location:** `backend/app/domain/exposure_layers.py`
  - **Description:** Canonical definition of `surface`, `deep`, and `constrained_dark` layers. Replaces the legacy `ConnectorLayer` enum.

- **Identifier Types (`IdentifierType`)**
  - **Location:** `backend/app/domain/linkage.py`
  - **Description:** Canonical definition of input identifier formats (email, phone, domain, etc.).

## 2. Core Entities

- **Findings (`Finding`)**
  - **Location:** `backend/app/schemas/finding.py` (Pydantic model), `backend/app/models/finding.py` (SQLAlchemy model)
  - **Description:** Represents a normalized exposure record found by a connector.

- **Scans (`Scan`)**
  - **Location:** `backend/app/schemas/scan.py`, `backend/app/models/scan.py`
  - **Description:** Represents a discovery operation across one or more layers.

- **Scores (`PDSS`)**
  - **Location:** `backend/app/schemas/score.py`
  - **Description:** Represents the Personal Data Severity Score. Configured by `shared/score_model/pdss_catalog.json`.

## 3. Privacy and Consent

- **Consent Log (`ConsentEgressLog`)**
  - **Location:** `backend/app/models/consent_egress.py`
  - **Description:** Immutable ledger tracking Amber discovery consent verification prior to egress.

## Guidelines for Adding Contracts

1. **Check First:** Before creating a new Enum or Model, consult this inventory and the `backend/app/domain/` directory.
2. **Single Source of Truth:** Do not duplicate domain definitions in SDKs or frontend types if they diverge conceptually from the backend models.
