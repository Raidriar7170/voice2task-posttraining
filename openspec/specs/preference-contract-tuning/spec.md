# preference-contract-tuning Specification

## Purpose
Define how DPO preference tuning uses chosen/rejected browser task contracts to prefer safer, more executable, and less ambiguous speech-to-contract outputs.
## Requirements
### Requirement: Train preference contract adapters
The system SHALL run DPO training over chosen/rejected browser task contract pairs to prefer safer, more executable, and less ambiguous contracts.

#### Scenario: Run DPO training
- **WHEN** a developer launches DPO training with a valid config and preference dataset path
- **THEN** the system trains a LoRA adapter or adapter continuation and records the base/SFT model reference, dataset manifest, hyperparameters, and training command

### Requirement: Validate chosen and rejected contracts
The system SHALL validate DPO pair structure before training.

#### Scenario: Reject weak preference pairs
- **WHEN** a DPO pair is missing a chosen contract, missing a rejected contract, uses different inputs across the pair, or lacks a rejection reason
- **THEN** the validator fails the pair and reports the pair identifier and failure category

### Requirement: Use meaningful rejection categories
The system SHALL categorize rejected contracts by contract-relevant failure type rather than relying only on random invalid JSON.

#### Scenario: Categorize hard negatives
- **WHEN** a rejected contract is generated or imported
- **THEN** it is labeled with a category such as wrong task type, wrong route, unsafe allowance, missing confirmation, missing slot, wrong slot, underspecified request, or malformed schema

### Requirement: Report DPO impact by slice
The system SHALL report DPO evaluation results by hard-negative and safety-relevant slices in addition to aggregate metrics.

#### Scenario: Generate DPO report
- **WHEN** DPO evaluation finishes
- **THEN** the report includes aggregate metrics and separate slices for route, safety, confirmation, slot, and schema failures
