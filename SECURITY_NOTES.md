# Security baseline – anonymous API exposure

## 2026-09-18

- GET /recipes
  - Anonymous requester
  - 200 OK
  - Returns **all** recipes, including `is_public: false` (private data exposure).

- PATCH /recipes/3
  - Anonymous requester
  - 200 OK
  - Successfully updates private recipe title ("Secret family hot sauce" → "Grandmas Stew [stolen]").

- DELETE /recipes/2
  - Anonymous requester
  - 204 NO CONTENT
  - Recipe 2 permanently deleted from collection.
