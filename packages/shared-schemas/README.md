# Shared Schemas

Pydantic v2 contracts for the v0.1 functional proteomics workbench core data model.

The Python models are the source of truth. TypeScript types are generated from the
exported JSON Schema with:

```sh
make gen-types
```

SQLModel table classes are intentionally deferred to the persistence/migrations work.
