# Changelog

## 0.5.0

Document pairing logic update.

- Added `Same document ID only` pairing mode for strict full-basename matching.
- Added `Same ID + all unmatched candidates` mode to compare every unmatched v1 x v2 candidate pair.
- Preserved missing-file rows in the dashboard while still allowing unmatched candidate comparisons.
- Replaced sorted one-by-one leftover pairing with complete candidate generation.
- Reduced the risk of misleading reports caused by comparing different document IDs inside the same logical group.
- Added candidate-specific report labels and filenames.
- Added regression tests for exact document ID matching and unmatched candidate pairing.

## 0.4.0

Comparison engine and structural summary update.

- Added ignore rules for volatile tags, attributes, timestamps, UUIDs, generated fields, and URLs.
- Added structural change summaries for nodes, attributes, and text.
- Improved large XML comparison accuracy by diffing normalized full-file line streams instead of independently comparing byte chunks.
- Restored visible comparison status indicators in the UI.
