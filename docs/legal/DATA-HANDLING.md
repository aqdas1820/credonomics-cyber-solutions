# Data handling — version 1.2.0

## Persistent local data

The default data directory is `%LOCALAPPDATA%/CredoNomicsCyberSolutions`, or `CREDONOMICS_DATA_DIR` when explicitly set. `workspace.sqlite3` contains JSON settings/branding/appearance, window position, last input/export folders, invoice counters, and resumes/invoices saved through the application's Save action. Folder preferences retain directory paths, not copies of customer documents. The schema is project-created. Saved records can contain names, phone numbers, addresses, invoice lines and other entered fields. Settings can retain a local logo path and optional support/website text. SQLite may create journal/locking files during transactions. There is no automatic expiry or encryption of this database. Machine ID is derived locally from a Windows identifier (or local hardware/hostname fallback) and shown in settings; it is not uploaded by application code.

Exports, screenshots and video recordings are written to operator-selected paths and remain until deleted by the operator. Screen recording writes video progressively, so interruption can leave a partial file. Removing an input from the current document list does not delete the original. Deleting a saved record removes the database row, not exported files or necessarily recoverable disk pages; no secure-erasure guarantee is made.

## Temporary files and memory

PDF/image previews and processing buffers normally use memory. Scanner transfer and external Office conversion use uniquely named, owner-marked job directories under `temporary-work` in the application's data directory. Context-managed cleanup runs on ordinary success/error paths. On startup, a background cleanup checks only this owned namespace and removes verified job directories whose owning process has exited. Active jobs, unmarked folders and customer-selected exports are not removed. Locked files, process-ID reuse or an inaccessible folder can defer cleanup. Legacy OS temporary folders from older builds are not automatically purged. Crashes or power loss can leave incomplete exports; no secure-erasure or guaranteed recovery claim is made. Memory, swap, thumbnails, backups and filesystem caches are controlled by the OS.

## Network and external components

Product processing code contains no telemetry, upload, cloud-account or automatic update service. Background-removal weights are not supplied or enabled in this source profile. Signature validation passes `allow_fetching=False`; online revocation checking is not performed. Installation scripts intentionally download Python dependencies and missing OCR data and verify provisioned asset hashes. Optional external Office converters, printer/scanner drivers, Windows printing (including network printers), OS services and user-selected remote filesystem locations have independent behavior; no blanket promise of zero network traffic is made for them. Legal-document viewers read local files and do not follow external links.

## Logs, cleanup and operator responsibilities

The production application writes a bounded local diagnostic event log under `diagnostics/events.jsonl`: startup/close, tool names, operation states, error types and code locations. It omits exception messages, document paths/content, OCR text, form values, signatures and previews. One current file and up to two backups are limited to approximately 512 KB each. Logs are never uploaded automatically. Explicit library logging environment variables (including PYMUPDF_LOG/PYMUPDF_MESSAGE) can direct third-party diagnostic output to files; retention follows that configuration. Native libraries, Windows error reporting, print spoolers and external converters may maintain their own logs/caches. Development capture/test entry points are excluded from the production EXE. Error details can include input paths and are displayed locally only on request. Printer spool retention follows driver/Windows configuration.

Use Saved records → Delete record for retained resume/invoice rows. Close the application before manually removing/backing up its data directory; this also removes settings/counters. Delete exports and leftover temporary folders separately after ensuring no active job uses them. Keep database/backups private and apply appropriate OS access controls. No claim of zero retention, immediate deletion, absolute security or secure erasure is made.


## Publisher contact and packaged storage

Developed and published by CredoNomics Investment Solutions.
Website: https://credonomics.in
Support email: support@credonomics.in
Support phone: 02562455327
Copyright © 2026 CredoNomics Investment Solutions. All rights reserved.

With Windows package identity, the default database is in `%LOCALAPPDATA%/Packages/<actual-package-family>/LocalState/workspace.sqlite3`. Portable storage and explicit data-directory overrides remain supported. The website/email buttons open external applications and never upload or attach documents automatically. A public app-specific privacy-policy URL is not yet supplied.
