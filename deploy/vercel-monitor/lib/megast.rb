# frozen_string_literal: true
# Copyright (c) 2026 Ingolf Lohmann. Repository licensing applies.
require 'json'

module QikvrtMegaST
  SOURCE_PATH = File.expand_path('../megast-source.json', __dir__)
  SHA256 = /\A[0-9a-f]{64}\z/
  COMMIT = /\A[0-9a-f]{40}\z/

  # This is a source descriptor, never a substitute for a live effect receipt.
  def self.source(path = SOURCE_PATH)
    value = JSON.parse(File.binread(path))
    archive = value.fetch('archive')
    netboot = value.fetch('netboot')
    transport = value.fetch('transport')
    raise ArgumentError, 'unexpected source schema' unless value['schema'] == 'qikvrt_megast_source_descriptor_v1'
    raise ArgumentError, 'unexpected source repository' unless value['repository'] == 'Goldkelch/qik-vrt'
    raise ArgumentError, 'invalid commit' unless COMMIT.match?(value.fetch('source_commit'))
    raise ArgumentError, 'invalid tree' unless COMMIT.match?(value.fetch('source_tree'))
    raise ArgumentError, 'invalid archive digest' unless SHA256.match?(archive.fetch('sha256'))
    raise ArgumentError, 'invalid manifest digest' unless SHA256.match?(netboot.fetch('manifest_sha256'))
    raise ArgumentError, 'invalid archive size' unless archive['bytes'].is_a?(Integer) && archive['bytes'].positive?
    raise ArgumentError, 'transport must not rebuild' unless archive['transport_rebuild_allowed'] == false
    short = value.fetch('source_commit')[0, 8]
    expected = (0..7).map { |i| format('qikvrt-megast-%s.part%02d.zip', short, i) }
    raise ArgumentError, 'incomplete or reordered transport' unless transport['part_names'] == expected
    # URL admission belongs to the reviewed release/readback path, not this API.
    raise ArgumentError, 'public URL admission not implemented' unless transport['public_download_urls'].nil?
    raise ArgumentError, 'part hashes not independently available' unless transport['part_hashes'].nil?
    value
  end

  def self.descriptor(environment = ENV)
    value = source
    deployment_commit = environment['VERCEL_GIT_COMMIT_SHA']
    deployment_commit = nil unless deployment_commit.is_a?(String) && COMMIT.match?(deployment_commit)
    {
      'schema' => 'qikvrt_megast_delivery_projection_v1',
      'role' => 'READ_ONLY_SOURCE_DESCRIPTOR',
      'source' => value,
      'deployment_commit_reported_by_environment' => deployment_commit,
      'deployment_commit_independently_verified' => false,
      'delivery' => {
        'state' => 'HOLD_UNVERIFIED',
        'blocker' => 'PUBLIC_RELEASE_BYTE_READBACK_REQUIRED',
        'next_action' => 'Complete native review and Main adoption, then reuse the existing Mega ST publish path and independently verify the original archive transport bytes.',
        'download_url' => nil,
        'public_delivery_verified' => false,
        'new_receiver_boot_verified' => false,
        'physical_atari_execution_verified' => false
      },
      'boundaries' => {
        'predecessor_evidence_transfer' => false,
        'main_adoption_implied' => false,
        'native_review_implied' => false,
        'ruleset_effect_implied' => false,
        'transport_ack_is_effect_ack' => false,
        'effect_ack_done' => false
      }
    }
  end
end
