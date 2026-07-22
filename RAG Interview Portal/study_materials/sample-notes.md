# Sample Study Material

## Big-O Notation

Big-O describes how runtime or space grows with input size.

| Algorithm | Best | Average | Worst |
|-----------|------|---------|-------|
| Quick Sort | O(n log n) | O(n log n) | O(n²) |
| Merge Sort | O(n log n) | O(n log n) | O(n log n) |
| Binary Search | O(1) | O(log n) | O(log n) |

## CAP Theorem

In a distributed system you can guarantee at most **two** of:

- **Consistency** — every read gets the latest write
- **Availability** — every request gets a response
- **Partition tolerance** — system works despite network splits

Since partitions happen in practice, you usually choose between CP and AP.

## SOLID Principles

1. **S**ingle Responsibility — one reason to change per class
2. **O**pen/Closed — open for extension, closed for modification
3. **L**iskov Substitution — subtypes must be substitutable
4. **I**nterface Segregation — many specific interfaces over one general
5. **D**ependency Inversion — depend on abstractions, not concretions
