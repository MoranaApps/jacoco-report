---
name: spring
description: Practices for Java backends built on Spring Boot - controllers and DTOs, services, Bean Validation, Spring Security, JPA and transactions, configuration, and JUnit tests. Use when adding or changing Spring endpoints, services, repositories or configuration, or reviewing such changes.
---

<!-- From agentic-defaults. Kit updates replace this file except a "## This project" section at the end, which belongs to the project. Edit nothing else. Rules for all work go in AGENTS.md "This project". -->

# Spring

Follow the project first. Read the backend's `CONTEXT.md` and one existing feature end to end (controller, DTOs, service, repository), and copy its shape: package layout, DTO mapping (MapStruct or by hand), exception handling. The project's conventions win over this list.

## Structure

- Controllers handle HTTP and DTOs. Services hold business rules and transactions. Spring Data repositories hold queries. Never return JPA entities from controllers; map them to DTOs.
- Use constructor injection with `final` fields, not `@Autowired` on fields.
- Settings live in `application.yml` or properties, bound with `@ConfigurationProperties`. Secrets come from the environment or a secret store, never from committed files.
- Use the starters and libraries already in the Maven or Gradle build. Don't add a second one for the same job.

## Requests

- Validate request DTOs with Bean Validation (`@Valid`, `@NotNull`, `@Size` and so on). Errors go through the project's `@RestControllerAdvice` as a 400 in its error format, for example `ProblemDetail`. No stack traces in responses.
- Check access on the specific record, not just the role: `@PreAuthorize` with an ownership check, or an explicit check in the service.
- Don't loosen the security configuration (`permitAll`, disabling CSRF, CORS wildcards) without approval.
- Keep the API compatible: add fields, don't rename or remove them.
- Keep the API contract accurate. If the project generates code from an OpenAPI file, change the file and regenerate; never edit generated code. If springdoc generates the spec from the code, keep DTOs and annotations complete so it matches the real behavior.

## JPA and transactions

- Put `@Transactional` on service methods that write, not on controllers. A `@Transactional` method called from another method in the same class runs without a transaction, because the call bypasses the proxy.
- Avoid N+1 queries and lazy-loading surprises: fetch joins or `@EntityGraph` for associations you need. Don't rely on open-session-in-view.
- Use derived queries, or `@Query` with named parameters. Never concatenate input into JPQL or SQL.
- Schema changes are Flyway or Liquibase migrations. That is relational-database work. Never use `ddl-auto=update` outside throwaway local experiments.

## Outbound calls and background work

- `RestClient`, `WebClient` and `RestTemplate` calls set connect and read timeouts.
- `@Async` and `@Scheduled` work is safe to run twice and handles its own failures.

## Tests

- Unit-test services with JUnit 5. Mock only collaborators at the edge, such as clients for other services.
- Test the web layer with `@WebMvcTest` and MockMvc: validation, status codes, and security with `@WithMockUser`.
- Test repositories and full flows against the real database engine. `(production)`: use Testcontainers if the project does. Avoid H2 standing in for PostgreSQL unless the project already accepts that.
- Run tests with the project's wrapper: `./mvnw test` or `./gradlew test`.

## Stop and report before

- a breaking change to an endpoint's request or response,
- adding a starter or other dependency,
- changing the security configuration or authentication,
- a schema change (relational-database-developer's work).
