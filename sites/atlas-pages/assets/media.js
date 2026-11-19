/* Curated videos and figures from the project folders. Captions follow the original reports. */
window.MEDIA = {
  pairs: [
    {
      title: 'Same start, two policy classes', id: 'stack_direct_20261001', date: '1 Oct 2026',
      text: 'Both models see the same two state frames and were trained for 30,000 updates on the same 180 two-cube demonstrations. The deterministic chunk regressor stacked 28/40 times, the diffusion policy 0/40.',
      left: { src: 'pair-direct-46000', label: 'Direct action-chunk regressor', tag: 'stacked', ok: true },
      right: { src: 'pair-diffusion-46000', label: 'Diffusion policy', tag: 'no stack', ok: false }
    },
    {
      title: 'Same start, one diagnostic intervention', id: 'stack_placement_20261001', date: '1 Oct 2026',
      text: 'Same diffusion checkpoint and the same start. On the right, only the horizontal (XY) actions after lifting are replaced by a simple feedback rule toward the target cube. Stacks rose from 0/20 to 9/20, which showed that the failures were centimetre-level transport errors, not release errors.',
      left: { src: 'pair-placement-baseline-46000', label: 'Original actions', tag: '0/20 overall', ok: false },
      right: { src: 'pair-placement-xy-46000', label: 'XY feedback after lift (diagnostic)', tag: '9/20 overall', ok: true }
    }
  ],
  robot: [
    { src: 'direct-stack-success-46003', title: 'Two-cube stack (direct regressor)', date: '1 Oct', id: 'stack_replication', ok: true,
      text: 'Stored stack criterion met; the audit still flags the transport as premature. Replay at 4 frames/s.' },
    { src: 'direct-stack-failure-46005', title: 'Missed grasp', date: '1 Oct', id: 'stack_replication', ok: false,
      text: 'Same model, different start: no grasp, no lift, no stack within 500 steps.' },
    { src: 'bc-state-stack-two', title: 'End-to-end BC baseline', date: '1 Oct', id: 'BASE-001', ok: false,
      text: 'One network for the whole task: 0/50 stacks. This started the stage-by-stage diagnosis.' },
    { src: 'diffusion-state-stack-two', title: 'Diffusion baseline', date: '1 Oct', id: 'BASE-002', ok: false,
      text: 'Diffusion policy on state input, same test scenes: 0/50.' },
    { src: 'lift-sensor-vs-state', title: 'Lift task: sensor error vs. real state change', date: '12 Oct', id: 'supervisor meeting', ok: null,
      text: 'Schematic animation, not experiment data. It explains the idea behind the earlier Lift extension, which reached 56/60 vs 44/60 for plain BC over three seeds.' }
  ],
  vision: [
    { src: 'vision-tower-extra-views', title: 'Extra hand-camera views of a tower', date: '2 Nov', id: 'visual_active_v3', ok: null,
      text: 'Two fixed cameras plus a hand camera. The arm moves for additional views and the 3D boxes are re-estimated (cyan: simulator truth, orange: first estimate, green: after the extra view). Technical test with three frozen M2 models.' },
    { src: 'vision-side-view', title: 'Wide side view (91° change)', date: '2 Nov', id: 'visual_active_v3', ok: false,
      text: 'A collision-checked view change of 48.6 cm. The new image did not help yet: scene error 12.4 → 18.2 mm-equivalent, so the update was not adopted.' },
    { src: 'vision-active-view', title: 'Collision-checked camera motion', date: '1 Nov', id: 'camera_planning', ok: null,
      text: 'Whole-arm motion to a new viewpoint, checked against joint limits, self-collision and the camera housing. Kinematic replay using simulator reference geometry.' },
    { src: 'vision-hand-camera', title: 'What the hand camera sees', date: '1 Nov', id: 'active_view', ok: null,
      text: 'Hand-camera image stream during the planned motion.' },
    { src: 'vision-two-cube-tower', title: 'Multi-view edge refinement', date: '3 Nov', id: 'VIS-001', ok: true,
      text: 'Edges tracked over a 40-image sequence correct the box pose of a two-cube tower: 3.9 → 2.9 mm-equivalent. Labels in German.' }
  ]
};
