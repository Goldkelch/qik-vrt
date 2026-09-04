import assert from 'node:assert/strict';
import {
  FANOUT,
  GATE_NAMES,
  RETIREMENT_DEPTH,
  bootstrapProjection,
  classifyGateSet,
  derealize,
  executeTerminalInput,
  fixedPointAlu,
  logicalNodeCount,
  manifestChildren,
  materializeMesh,
  rootNode
} from './api/_mesh.js';

const subject = {
  repository: 'Goldkelch/qik-vrt',
  kind: 'pull_request',
  number: 992,
  head_branch: 'ui/vercel-eight-gates-live-v1',
  head_sha: 'c'.repeat(40)
};
const payload = {kind: 'DATA', value: 'universell gebunden'};
const root = rootNode(subject, 0);
const children = manifestChildren(root, payload);
assert.equal(children.length, FANOUT);
assert.deepEqual(children.map(child => child.slot), [0,1,2,3,4,5,6,7]);
assert.deepEqual(children.filter(child => child.terminal).map(child => child.slot), [0,7]);
assert.ok(children.every(child => child.authority_node_id === root.node_id));
const grandChildren = manifestChildren(children[2], payload);
assert.equal(grandChildren.length, FANOUT);
assert.ok(grandChildren.every(child => child.authority_node_id === children[2].node_id));
assert.deepEqual(grandChildren[0].path, [2,0]);

const recovered = derealize(root, children);
assert.equal(recovered.lossless, true);
assert.deepEqual(recovered.payload, payload);

const mesh = materializeMesh(subject, payload, 2, 4);
assert.equal(mesh.materialized_node_count, 73);
assert.equal(mesh.logical_node_count_at_retirement_depth, '153391689');
assert.equal(logicalNodeCount(2).toString(), '73');
assert.equal(mesh.polling, false);
assert.equal(mesh.framework, 'KubiKAva');

const add = fixedPointAlu({operation: 'ADD', a_raw: 384, b_raw: 128, bits: 16, fractional_bits: 8});
assert.equal(add.state, 'CONTINUE');
assert.equal(add.result_raw, '512');
assert.equal(add.result_decimal, '2');
const mac = fixedPointAlu({operation: 'MAC', a_raw: 384, b_raw: 128, accumulator_raw: 64, bits: 16, fractional_bits: 8});
assert.equal(mac.result_raw, '256');
assert.equal(mac.result_decimal, '1');
const overflow = fixedPointAlu({operation: 'ADD', a_raw: 127, b_raw: 1, bits: 8, fractional_bits: 0});
assert.equal(overflow.state, 'HOLD');
assert.equal(overflow.result_raw, null);

const allHold = classifyGateSet(
  GATE_NAMES.map(name => ({name, state: 'HOLD'})),
  RETIREMENT_DEPTH,
  true
);
assert.equal(allHold.state, 'RETIRE_CANDIDATE');
assert.equal(allHold.action, 'PREPARE_EXACT_CARRIER_RETIREMENT');
assert.equal(allHold.hold_admissible, false);
const afterCut = classifyGateSet(
  GATE_NAMES.map(name => ({name, state: 'HOLD'})),
  RETIREMENT_DEPTH,
  false
);
assert.equal(afterCut.state, 'HOLD');
assert.equal(afterCut.hold_admissible, true);

const transition = executeTerminalInput(subject, {
  schema: 'qikvrt_terminal_input_v1',
  materialized_depth: 2,
  tick: 9,
  command: {
    kind: 'FIXED_POINT_ALU',
    operation: 'MAC',
    a_raw: 384,
    b_raw: 128,
    accumulator_raw: 64,
    bits: 16,
    fractional_bits: 8
  }
});
assert.equal(transition.mesh.materialized_node_count, 73);
assert.equal(transition.first_level_derealization.lossless, true);
assert.equal(transition.terminal_pattern.SUCCESSOR, 'EIGHT_CHILD_AUTHORITIES');
assert.equal(transition.effect_ack, false);

const bootstrap = bootstrapProjection();
assert.equal(bootstrap.transport.polling, false);
assert.equal(bootstrap.mesh.nodes.filter(node => node.depth === 1).length, FANOUT);

console.log(JSON.stringify({
  schema: 'qikvrt_metatransistor_js_test_receipt_v1',
  fanout: FANOUT,
  depth9_nodes: logicalNodeCount(RETIREMENT_DEPTH).toString(),
  fixed_point_result_raw: mac.result_raw,
  lossless_derealization: recovered.lossless,
  retirement_state: allHold.state,
  tests: 'SUCCESS'
}));
