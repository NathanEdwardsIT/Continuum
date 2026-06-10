"""Seed example notes for demonstration."""

from __future__ import annotations

from knowledgevault.services.note_service import NoteService

EXAMPLE_NOTES = [
    {
        "title": "Python Async Patterns",
        "content": """# Python Async Patterns

Learning about asyncio and concurrent programming in Python.

## Key Concepts
- `async`/`await` syntax for coroutines
- Event loops manage concurrent tasks
- `asyncio.gather()` runs multiple coroutines

## Use Cases
- Web scraping with aiohttp
- Database connection pooling
- Real-time API servers with FastAPI

The async model is essential for building scalable network applications.
""",
    },
    {
        "title": "Q1 Budget Review",
        "content": """# Q1 Budget Review

## Revenue
- Product sales: $45,000
- Consulting: $12,000
- Total revenue: $57,000

## Expenses
- Office rent: $3,600
- Software subscriptions: $890
- Marketing: $2,400

## Savings Goal
Targeting 20% savings rate this quarter. Current portfolio allocation:
- 60% index funds
- 25% bonds
- 15% individual stocks
""",
    },
    {
        "title": "Machine Learning Study Notes",
        "content": """# Machine Learning Study Notes

## Course: Introduction to ML

### Lecture 3: Supervised Learning
- Classification vs regression
- Training/validation/test splits
- Overfitting and regularization

### Key Algorithms
1. Linear regression
2. Logistic regression
3. Decision trees
4. Random forests

### Assignment Due
Complete the homework on gradient descent by Friday.
Research paper on neural networks for next week's lecture.
""",
    },
    {
        "title": "Sprint Planning - Project Atlas",
        "content": """# Sprint Planning - Project Atlas

## Team Meeting Notes
Date: This week

### Sprint Goals
- Complete user authentication module
- Deploy staging environment
- Fix critical bugs from last release

### Tasks
- [ ] API endpoint for user registration
- [ ] JWT token implementation
- [ ] Database migration for users table
- [ ] Client presentation on Friday

### Stakeholder Update
Manager wants deliverable demo by end of sprint.
Client feedback on the prototype was positive.
""",
    },
    {
        "title": "Weekend Hiking Trip",
        "content": """# Weekend Hiking Trip

Planning a personal hiking adventure this Saturday.

## Trail: Eagle Peak Loop
- Distance: 8 miles
- Elevation gain: 2,100 ft
- Difficulty: Moderate

## Packing List
- Water (2L minimum)
- Trail snacks and lunch
- First aid kit
- Camera for photos

Looking forward to some time in nature with friends.
Great for fitness and mental wellness.
""",
    },
    {
        "title": "React Component Architecture",
        "content": """# React Component Architecture

## Project Structure
Building a scalable frontend with React and TypeScript.

### Patterns
- Container/presenter separation
- Custom hooks for shared logic
- Context API for global state

### Code Example
```javascript
function useNotes() {
  const [notes, setNotes] = useState([]);
  // fetch and manage notes
  return { notes, addNote, deleteNote };
}
```

### Best Practices
- Keep components small and focused
- Use TypeScript for type safety
- Write unit tests with Jest
""",
    },
    {
        "title": "Investment Portfolio Rebalance",
        "content": """# Investment Portfolio Rebalance

## Current Allocation
Reviewing my financial portfolio for the new year.

| Asset | Current | Target |
|-------|---------|--------|
| Stocks | 55% | 60% |
| Bonds | 30% | 25% |
| Cash | 15% | 15% |

## Actions
- Buy $2,000 in VTI index fund
- Sell $1,500 in bond ETF
- Increase 401k contribution to 15%

Tax implications considered. Consulting with financial advisor next week.
""",
    },
    {
        "title": "Database Indexing Strategies",
        "content": """# Database Indexing Strategies

## SQL Performance Optimization

### When to Index
- Columns in WHERE clauses
- Foreign key columns
- Columns used in JOINs
- ORDER BY columns

### Index Types
- B-tree (default in SQLite, PostgreSQL)
- Hash indexes for equality lookups
- Full-text search indexes (FTS5)

### Python Example
Using SQLite with proper indexing for a notes application.
The repository pattern helps organize database queries cleanly.
""",
    },
]


def seed_example_notes(service: NoteService | None = None) -> None:
    """Populate the database with example notes if empty."""
    owned = service is None
    service = service or NoteService()
    if service.repository.count_notes() > 0:
        if owned:
            service.close()
        return

    for note_data in EXAMPLE_NOTES:
        service.create_note(note_data["title"], note_data["content"])

    if owned:
        service.close()
