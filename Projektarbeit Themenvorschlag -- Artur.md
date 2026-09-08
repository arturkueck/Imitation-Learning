
### **Plan A:**
- Read through IL models, BC variants ( maybe based on Robomimics library ) 
	-  Read robomimic and try to recognise weak point or points that may be optimised with further implementation 
- Research other possible extensions, optimisations or BC algorithms to extend 
	- Literature Review of possible behavioural cloning extension, algorithms and evaluation of their advantage in comparison with robomimics BC algorithms
- Familiarisation with the library work & datasets
- Implement the chosen implementation in the robomimic framework 
- Train with the available datasets (choose suitable sets)
	- (Due to time plan reasons and possible training challenges, it is possible to choose a small (franka) manipulatiom dataset)
- Compare and evaluate with robomimics results  
- Documentation 

### **Plan B:** If there is no good possibilty for testing new algorithm or optimisations

- Find online suitable datasets (mentioned by robomimic) OR/AND collect a small simulation dataset 
	- Choice of 1 or 2 relevant manipulation task with a certain challenge degree presenting 
     variation to the robomimic or the state of the art
- Resume training of the robomimic pretrained model (finetuning)
- Evaluate the generalisation to a new task & Compare


DAGGER
BC - ACT 
BC - Diffusion Policy ... 
 
## **Um in den Thema rein zu kommen - Highlight papers and links**
Robomimic
https://robomimic.github.io/
### What I've been reading
Robotic Manipulation via Imitation Learning: Taxonomy, Evolution, Benchmark, and Challenges
https://arxiv.org/abs/2508.17449
RoboCopilot: Human-in-the-loop Interactive Imitation Learning for Robot Manipulation
https://arxiv.org/abs/2503.07771
Dexterous Manipulation through Imitation Learning: A Survey
https://arxiv.org/abs/2504.03515
Universal Manipulation Interface: In-The-Wild Robot Teaching Without In-The-Wild Robots
https://umi-gripper.github.io/

### **Maybe relevant for this project:** 

Variants of BC Algorithms_ !! Focus on novelty to robomimic library 
	# Diffusion model augmented BC: https://proceedings.mlr.press/v235/chen24as.html 
	# Stable-BC: Controlling Covariate Shift with Stable Behavior Cloning https://collab.me.vt.edu/Stable-BC/
	# DiffClone: Enhanced Behaviour Cloning in Robotics with Diffusion-Driven   Policy  Learning https://arxiv.org/abs/2401.09243
	....)
	# DART: Noise Injection for Robust Imitation Learning  https://proceedings.mlr.press/v78/laskey17a/laskey17a.pdf

### Some helpful research tools: 
Connected papers https://www.connectedpapers.com/
Rabbit Paper https://www.researchrabbit.ai/
Zotero https://www.zotero.org/ (could be integrated with rabbit paper)
Obsidian (to create a mind map, notes and link them using the canvas function)  https://obsidian.md/