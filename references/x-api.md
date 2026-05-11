# X API notes for x-link-reader

## Endpoint

Use the official X API tweet lookup endpoint:

```text
GET https://api.x.com/2/tweets/{id}
```

## Auth

Preferred auth is a bearer token sent as:

```text
Authorization: Bearer <token>
```

If only an API key and API secret are available, the CLI can mint a bearer token using:

```text
POST https://api.x.com/oauth2/token
grant_type=client_credentials
```

## Required fields for full text

Request these tweet fields:

```text
tweet.fields=note_tweet,article,entities,author_id,created_at
```

## Extraction priority

Use text in this order:

1. `data.article.text`
2. `data.note_tweet.text`
3. `data.text`

## Supported URL patterns

- `https://x.com/<user>/status/<id>`
- `https://twitter.com/<user>/status/<id>`
- `https://x.com/i/article/<id>`
- `https://x.com/i/articles/<id>`

## Output contract

The CLI should return structured JSON containing:

- `id`
- `input`
- `url_kind`
- `content_type`
- `text`
- `display_text`
- `author_id`
- `created_at`
- `api_url`

## Expected API behavior

- Regular posts: use `data.text`
- Long-form posts: `data.note_tweet.text`
- Article links: `data.article.text`

## Error handling

- Unsupported URL: exit non-zero with a clear message
- Missing auth: exit non-zero with setup guidance
- X API error: return the response status and first useful error message
