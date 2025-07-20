#  List Names  (with pagination, filters, search)
## /names

### GET
 sample url: GET /names?search=tech&ordering=-score&page=2

Response body:
{
  "count": 103,
  "next": "...",
  "previous": "...",
  "results": [
    {
      "id": 17,
      "domain_name": "TechGuru.co",
      ...
      "saved": true
    },
    ...
  ]
}


# Get Name Details
GET /names/17

Sample response:
{
  "id": 17,
  "domain_name": "TechGuru.co",
  ...
  "saved": true
}






# Toggle Save
POST /names/17/toggle-save

First call (saves):
→ { "saved": true }

Second call (unsaves):
→ { "saved": false }





## /api/saved-names

### POST
Headers:
Authorization: Bearer <Clerk Token>

Request body:
{
  "name_id": "<UUID of a Name object>"
}


Response body:
1.If name was saved:
{ "message": "Name saved" }


2.If already saved (and unsaved on toggle):
{ "message": "Name unsaved" }



## GET
Headers:
Authorization: Bearer <Clerk Token>

Query Params (optional):

start_date=YYYY-MM-DD (2025-07-17)

end_date=YYYY-MM-DD (2025-07-17)

ordering=created_at,-domain_name

search=example (when I enable search_fields)

domain_list=deleted, pending_delete, marketplace

status=available, taken, pending


### Usage Table
| Action        | Parameter(s) used                | Example Key(s)                                          | Notes                            |
|---------------|----------------------------------|---------------------------------------------------------|----------------------------------|
| **Search**    | `search`                         | `?search=ai`                                            | Must be enabled via `SearchFilter` + `search_fields` |
| **Filter**    | Custom query params              | `?start_date=2024-07-01&end_date=2024-07-16`           | We defined these manually in the view logic         |
| **Ordering**  | `ordering`                       | `?ordering=created_at` or `?ordering=-created_at`      | Uses `OrderingFilter`                               |
| **Pagination**| `page`, `page_size`              | `?page=2&page_size=20`                                 | DRF’s pagination settings apply                     |
| **Combined**  | All of the above                 | Mixed query string                                     | Order doesn't matter, just connect with `&`         |




## /api/acquired-names

### POST
Headers:
Authorization: Bearer <Clerk Token>

Request body:
{
  "name_id": "<UUID of a Name object>"
}


Response body:
1.If name was saved:
{ "message": "Name saved" }


2.If already saved (and unsaved on toggle):
{ "message": "Name unsaved" }



## GET
Headers:
Authorization: Bearer <Clerk Token>

Query Params (optional):

start_date=YYYY-MM-DD

end_date=YYYY-MM-DD

ordering=created_at,-domain_name

search=example (when I enable search_fields)

domain_list=deleted, pending_delete, marketplace

status=available, taken, pending

