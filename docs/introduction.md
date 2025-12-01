# Introduction to Pairwise Comparison

## The Challenge of Prioritization

In software development and product management, prioritizing features or requirements is a constant challenge. Stakeholders often struggle to assign absolute values (like "High", "Medium", "Low" or 1-10 scores) to a long list of items. This often leads to:

*   **The "Everything is High Priority" Syndrome**: When everything is important, nothing is.
*   **Cognitive Overload**: Comparing one item against an abstract scale is difficult and subjective.
*   **Inconsistency**: A "5" today might be a "7" tomorrow depending on mood or context.

## Why Pairwise Comparison?

Pairwise comparison simplifies this process by breaking it down into the smallest possible unit of decision-making: **comparing two items against each other**.

Instead of asking "How valuable is Feature A on a scale of 1 to 10?", we ask: **"Is Feature A more valuable than Feature B?"**

### Cognitive Benefits

*   **Relative vs. Absolute Judgment**: Humans are significantly better at making relative judgments (comparing A to B) than absolute judgments (rating A in isolation).
*   **Reduced Context Switching**: The decision maker only needs to focus on two items at a time.
*   **Faster Decisions**: Binary choices are quicker to make than nuanced scoring.

## How OneSelect Works

OneSelect leverages the power of pairwise comparison but solves its main drawback: the number of comparisons.

In a naive approach, comparing every item against every other item requires $O(N^2)$ comparisons. For 50 features, that's 1,225 comparisons—far too many for a human.

OneSelect uses **Bayesian Inference** and **Active Learning** to:

1.  **Select the most informative pairs**: It chooses the pair of items that, if compared, will give the most information about the overall ranking (reducing uncertainty).
2.  **Infer rankings**: It updates the estimated score and confidence interval for every item after each comparison.
3.  **Stop early**: You don't need to compare everything. The system stops when it has enough certainty to rank the items reliably.

This allows you to rank a large backlog with a fraction of the effort required for full manual sorting, while maintaining high mathematical rigor.

## Authentication and Security

OneSelect uses industry-standard authentication mechanisms to protect your data and ensure secure access to the API.

### JWT Tokens

OneSelect uses **JWT (JSON Web Token)** for authentication. A JWT is a compact, URL-safe token that contains encoded claims about the user's identity and permissions.

#### What is a JWT?

A JWT consists of three parts separated by dots (`.`):

```
header.payload.signature
```

1. **Header**: Contains metadata about the token type and signing algorithm
2. **Payload**: Contains claims (user data, permissions, expiration time)
3. **Signature**: Cryptographic signature to verify the token hasn't been tampered with

Example JWT:
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c
```

#### How Authentication Works

1. **Login**: Send your credentials to `/api/v1/auth/login`
2. **Receive Token**: The API returns a JWT token
3. **Use Token**: Include the token in the `Authorization` header for all subsequent requests:
   ```
   Authorization: Bearer <your-jwt-token>
   ```
4. **Token Expiration**: Tokens expire after a set period (typically 24 hours). Use the refresh endpoint to get a new token without re-entering credentials.

#### Security Benefits

- **Stateless**: The server doesn't need to store session data
- **Tamper-Proof**: The cryptographic signature prevents token modification
- **Self-Contained**: All necessary information is encoded in the token
- **Expiring**: Tokens have a limited lifetime to reduce security risks

### User Roles

OneSelect supports two user roles:

- **User**: Standard access to create projects and perform comparisons
- **Root/Superuser**: Administrative access including user management and system administration

Role-based permissions ensure that sensitive operations are restricted to authorized users only.
