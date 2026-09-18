const examples = {
  step: {tag: 'A / NEXT STEP', title: 'Place the beam.', body: 'The base and supports are correct. Read the instruction and predict the beam’s placement. This isolates one spatial decision.', rule: 'Can the model infer the right position and orientation?', description: 'Schematic: a verified base and supports, with the next beam to place.'},
  build: {tag: 'B / WHOLE BUILD', title: 'Carry the build forward.', body: 'The model assembled every piece itself. The beam only lands correctly if the earlier supports are in the right places. No correct state is supplied between steps.', rule: 'Do local decisions add up to a correct complete object?', description: 'Schematic: the assembled bridge, including the model’s own earlier placements.'},
  repair: {tag: 'C / REPAIR', title: 'Find the shifted support.', body: 'One support is displaced. The model must identify and correct it while preserving the rest of the build. In the actual task, the error would not be highlighted.', rule: 'Can it restore the intended structure with a minimal change?', description: 'Schematic explanation: the right support is shifted and highlighted for the reader.'}
};
const buttons = document.querySelectorAll('[data-mode]');
function showExample(mode) {
  const example = examples[mode];
  if (!example) return;
  for (const button of buttons) button.setAttribute('aria-pressed', String(button.dataset.mode === mode));
  document.getElementById('example-tag').textContent = example.tag;
  document.getElementById('example-title').textContent = example.title;
  document.getElementById('example-body').textContent = example.body;
  document.getElementById('example-rule').textContent = example.rule;
  document.getElementById('diagram-title').textContent = example.description;
  document.getElementById('top-beam').setAttribute('transform', mode === 'step' ? 'translate(0 0)' : 'translate(0 37)');
  document.getElementById('right-support').setAttribute('transform', mode === 'repair' ? 'translate(24 0)' : 'translate(0 0)');
  document.getElementById('placement-arrow').setAttribute('visibility', mode === 'step' ? 'visible' : 'hidden');
  document.getElementById('error-outline').setAttribute('visibility', mode === 'repair' ? 'visible' : 'hidden');
}
for (const button of buttons) button.addEventListener('click', () => showExample(button.dataset.mode));
