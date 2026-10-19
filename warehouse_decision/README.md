# Decision engine

The decision engine reads the box database and chooses a pending task using a transparent heuristic based on priority, pickup distance and weight. Battery state can force a charging decision when the battery is low.

When the camera confirms the current box ID, the engine requests pickup, then sends a Nav2 goal to the box destination. After placement, the task is removed from the pending set and the next task is selected.

If a different box with a higher priority is detected while waiting for the current box, the engine publishes a `REPLAN_REQUIRED` decision event. This is the extension point for a more advanced optimizer or ML-based scheduler.
