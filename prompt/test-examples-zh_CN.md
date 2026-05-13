# Todo Management Agent - Test Prompts

Use these prompts to test and evaluate the Todo Management Agent's capabilities.

## Basic Task Management Tests

### Test 1: Simple Task Creation
**Prompt:**
```
我需要完成一个项目报告，包括数据收集、分析和撰写。
能帮我把这个分解成更小的任务吗？
```

**Expected Output:**
- Break down into 3-4 subtasks with descriptions
- Suggest task sequence and dependencies
- Estimate effort for each subtask

---

### Test 2: Project Organization
**Prompt:**
```
我正在处理三个项目：
- 产品开发：前端、后端、测试
- 市场营销：内容创作、社交媒体、分析
- 人力资源：招聘、培训、评估

如何最好地组织这些任务？
```

**Expected Output:**
- Suggest project structure and hierarchy
- Recommend task grouping by priority or timeline
- Propose workflow optimizations

---

### Test 3: Priority Analysis
**Prompt:**
```
这周我有很多任务。帮我按优先级排序：
- 完成客户报告（周五截止）
- 学习新技术
- 参加团队会议（周三）
- 代码审查（待处理）
- 写文档
```

**Expected Output:**
- Prioritized task list with reasoning
- Identify critical path items
- Flag time-sensitive tasks
- Suggest parallel execution opportunities

---

## Calendar Integration Tests

### Test 4: Calendar Analysis
**Prompt:**
```
分析我的日历，告诉我可以完成哪些任务。
我明天有：
- 9:00-10:00 团队站会
- 14:00-15:30 客户会议
- 其余时间自由
```

**Expected Output:**
- Suggest 2-3 hour tasks that fit in free slots
- Recommend task types by context
- Identify focus time opportunities

---

### Test 5: Event-to-Todo Conversion
**Prompt:**
```
从这个会议备注中提取待办事项：

会议：Q2 产品规划
出席者：产品、工程、设计
讨论事项：
1. 新功能需求评估
2. 设计稿评审
3. 工程估算
行动项：
- 产品：收集需求文档
- 设计：完成高保真原型
- 工程：技术可行性分析
```

**Expected Output:**
- Extract 3 concrete action items
- Assign to appropriate owners if mentioned
- Set realistic deadlines
- Include related context

---

## Advanced Analytics Tests

### Test 6: Task Pattern Analysis
**Prompt:**
```
我最近完成的任务：
- 代码审查：每周3次，30分钟
- 文档编写：每月1-2次，2小时
- 会议参加：每周5-6次，1-2小时
- 实际开发：有空闲时才做

能分析一下我的时间分配吗？有什么改进建议？
```

**Expected Output:**
- Analyze time allocation patterns
- Identify time-consuming low-value activities
- Suggest optimization strategies
- Recommend process improvements

---

### Test 7: Workload Balancing
**Prompt:**
```
我的团队有5个人，需要分配这些工作：
- 功能1开发（预计40小时）
- 测试（预计20小时）
- 文档（预计10小时）
- 运维支持（预计10小时）
- 知识转移（预计5小时）

如何最优分配？
```

**Expected Output:**
- Suggest balanced workload distribution
- Consider role matching
- Identify potential bottlenecks
- Recommend phased approach if needed

---

## Workflow Optimization Tests

### Test 8: Multi-Project Scheduling
**Prompt:**
```
两个项目都在进行中，我需要：
项目A: 2周内交付（6个任务）
项目B: 3周内交付（8个任务）

如何制定交付计划？
```

**Expected Output:**
- Create timeline for both projects
- Identify critical milestones
- Suggest resource allocation
- Flag potential conflicts

---

### Test 9: Risk and Dependency Analysis
**Prompt:**
```
这些任务有依赖关系：
A → B → C (串联)
A → D (并联)
D → E (串联)

如果A需要2天，B需要3天，C需要1天，
D需要4天，E需要2天，
整个项目需要多长时间完成？
```

**Expected Output:**
- Calculate critical path (A→D→E = 8 days)
- Identify parallel opportunities
- Suggest parallelization
- Recommend buffer allocation

---

## Data Generation Test

### Test 10: Bulk Testing
**Prompt:**
```
生成500条测试任务数据用于性能测试。
需要包含：
- 不同的优先级
- 不同的项目
- 不同的状态（待做、进行中、完成）
```

**Expected Output:**
- Generate 500 diverse todo items
- Mix of projects and priorities
- Realistic distribution of statuses
- Suitable for load testing

---

## Conversation Flow Tests

### Test 11: Multi-turn Conversation
**Prompt 1:**
```
我想规划下个月的工作。
```

**Follow-up:**
```
我有4个主要项目，每个预计40小时。
```

**Follow-up:**
```
我每周工作40小时，有两周假期。
```

**Expected:**
- Understand context accumulation
- Refine recommendations based on new info
- Maintain conversation continuity

---

### Test 12: Clarification Questions
**Prompt:**
```
帮我组织一下工作。
```

**Expected Output:**
- Ask clarifying questions:
  - 您有多少项目？
  - 优先考虑什么？
  - 有具体的截止日期吗？
  - 你更喜欢什么工作方式？
- Use answers to provide targeted recommendations

---

## Error Handling Tests

### Test 13: Vague Request Handling
**Prompt:**
```
我很忙。
```

**Expected Output:**
- Ask for specifics
- Offer to help with specific areas
- Suggest starting points

---

### Test 14: Conflicting Requirements
**Prompt:**
```
我想这周完成10个复杂任务，每个需要8小时，但我只有15小时空闲。
```

**Expected Output:**
- Point out the conflict
- Ask clarification questions
- Suggest realistic alternatives
- Help prioritize if needed

---

## Success Metrics

For each test, evaluate:
✓ Relevance - Is the response on-topic?
✓ Actionability - Can user act on suggestions?
✓ Completeness - Does it address all aspects?
✓ Clarity - Is the response well-structured?
✓ Creativity - Does it offer novel insights?
