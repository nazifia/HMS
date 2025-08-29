# Medication Transfer Process Diagram

```mermaid
graph TD
    A[Bulk Store] -->|MedicationTransfer| B(Active Store)
    B -->|DispensaryTransfer| C[Dispensary]
    
    D[Pack Order Created] --> E{Process Order}
    E --> F[Check Active Store Inventory]
    F --> G{Medication Available?}
    G -->|No| H[Transfer from Bulk Store]
    G -->|Yes| I[Check Dispensary Inventory]
    H --> I
    I --> J{Sufficient Quantity?}
    J -->|No| K[Calculate Shortage]
    J -->|Yes| L[No Action Needed]
    K --> M[Create Dispensary Transfer]
    M --> N[Execute Transfer]
    N --> O[Update Inventories]
    L --> P[Create Prescription]
    O --> P
    P --> Q[Pack Order Ready]
    
    style A fill:#e1f5fe
    style B fill:#f3e5f5
    style C fill:#e8f5e8
    style D fill:#fff3e0
    style Q fill:#f1f8e9
```

## Process Flow Explanation

1. **Bulk Store to Active Store**:
   - Medications are initially stored in the Bulk Store
   - Transferred to Active Store as needed via MedicationTransfer

2. **Active Store to Dispensary**:
   - Medications in Active Store are transferred to Dispensary via DispensaryTransfer
   - This happens automatically when processing Pack Orders

3. **Pack Order Processing**:
   - When a Pack Order is created, it triggers the transfer process
   - System checks inventory levels at each stage
   - Automatically creates transfers when needed
   - Updates all inventory records after successful transfers

## Key Components

- **MedicationTransfer**: Moves medications from Bulk Store to Active Store
- **DispensaryTransfer**: Moves medications from Active Store to Dispensary
- **Inventory Models**: Track medication quantities at each location
- **PackOrder.process_order()**: Orchestrates the entire transfer process