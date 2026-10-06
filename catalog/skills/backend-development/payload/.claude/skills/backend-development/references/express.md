# Express / Node backend reference

- Structure: `routes/` (HTTP wiring) → `services/` (logic) → `repositories/` or ORM models (data).
- Validate bodies, params and queries with the project's schema library (zod, joi, class-validator) in middleware.
- Always `await` async work and forward errors to the error middleware (`next(err)`); unhandled rejections crash or hang requests.
- Central error middleware maps domain errors to status codes; never send `err.stack` to clients.
- Use `helmet`, CORS allow-lists and rate limiting where the project already does.
- Config from `process.env` through one config module with validation at startup.
- Tests: supertest against the app instance; mock only external services.
