# Development Rules & Architectural Governance

**Project:** Adaptive Variable Resolution 2.5D LiDAR Mapping System  
**Authority:** Lead Systems Architect  
**Document Status:** MANDATORY COMPLIANCE  

---

# Agent Rules

1. **Architecture Freeze is the highest authority.**  
   All development activities, feature additions, bug fixes, and agent interactions must conform strictly to `docs/ARCHITECTURE_FREEZE.md`. No proposal or implementation that violates the frozen specification is permitted.

2. **No agent can modify architecture silently.**  
   Architectural boundaries, data flows, topic definitions, and module responsibilities cannot be altered without explicit, documented architectural approval.

3. **Every code change requires:**
   - **Reason:** A clear, justifiable problem statement or feature requirement.
   - **Affected modules:** An explicit list of all files, packages, and classes impacted.
   - **Validation method:** Demonstration of test execution (e.g., `python verify_simulation.py` or unit test output) proving zero regressions.

4. **Existing interfaces must remain stable.**  
   All frozen interfaces specified in Section 13 of `docs/ARCHITECTURE_FREEZE.md` (ROS2 topic names, message types, WebSocket JSON schema keys, dataclass structures, and parameter keys) are immutable. Breaking changes are prohibited.

5. **No refactoring during feature implementation.**  
   Refactoring and cosmetic restructuring during feature implementation or bug resolution are strictly forbidden. Changes must focus exclusively on the targeted task without collateral file modification.

6. **No removal of code without evidence.**  
   No module, function, script, dataset, or configuration file may be removed without verifiable proof that it is non-functional, obsolete, and completely unreferenced across build, runtime, and documentation systems.
