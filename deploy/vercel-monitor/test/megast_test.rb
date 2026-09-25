# frozen_string_literal: true
require 'minitest/autorun'
require 'tempfile'
require 'webrick'
require_relative '../lib/megast'
require_relative '../lib/rails_bridge'

class MegaSTTest < Minitest::Test
  def test_original_archive_pin
    source = QikvrtMegaST.source
    assert_equal '2fdcf8d233b1495732ef38e3406ebfc095fd0ef3', source['source_commit']
    assert_equal 3_298_453_805, source['archive']['bytes']
    assert_equal '762fccec9f80bc83ac0475d5fdc3627dd370ad5ac8aabaa6d1c878de20a1bb76', source['archive']['sha256']
    assert_equal 'b0f33a6f9385ab72b42737165a427e3c33df49295c13cb10da70562fea9b1701', source['netboot']['manifest_sha256']
  end

  def test_exact_eight_parts
    names = QikvrtMegaST.source['transport']['part_names']
    assert_equal 8, names.uniq.length
    assert_equal 'qikvrt-megast-2fdcf8d2.part00.zip', names.first
    assert_equal 'qikvrt-megast-2fdcf8d2.part07.zip', names.last
  end

  def test_no_claim_promotion
    value = QikvrtMegaST.descriptor({})
    assert_nil value['delivery']['download_url']
    assert_equal 'HOLD_UNVERIFIED', value['delivery']['state']
    value['boundaries'].each_value { |v| assert_equal false, v }
    %w[public_delivery_verified new_receiver_boot_verified physical_atari_execution_verified].each do |key|
      assert_equal false, value['delivery'][key]
    end
  end

  def test_deployment_and_archive_subjects_are_separate
    value = QikvrtMegaST.descriptor('VERCEL_GIT_COMMIT_SHA' => 'a' * 40)
    assert_equal 'a' * 40, value['deployment_commit_reported_by_environment']
    assert_equal false, value['deployment_commit_independently_verified']
    refute_equal value['source']['source_commit'], value['deployment_commit_reported_by_environment']
    assert_nil QikvrtMegaST.descriptor('VERCEL_GIT_COMMIT_SHA' => 'main')['deployment_commit_reported_by_environment']
  end

  def test_source_mutations_fail_closed
    mutations = [
      ->(x) { x['schema'] = 'unexpected' },
      ->(x) { x['repository'] = 'other/repo' },
      ->(x) { x['archive']['sha256'] = 'not-a-digest' },
      ->(x) { x['source_commit'] = 'main' },
      ->(x) { x['archive']['bytes'] = '3298453805' },
      ->(x) { x['archive']['transport_rebuild_allowed'] = true },
      ->(x) { x['transport']['part_names'].pop },
      ->(x) { x['transport']['part_names'].reverse! },
      ->(x) { x['transport']['public_download_urls'] = ['https://example.org/fake.zip'] },
      ->(x) { x['transport']['part_hashes'] = ['0' * 64] }
    ]
    mutations.each do |mutate|
      source = QikvrtMegaST.source
      mutate.call(source)
      Tempfile.create('megast') do |file|
        file.write(JSON.generate(source)); file.flush
        assert_raises(ArgumentError) { QikvrtMegaST.source(file.path) }
      end
    end
  end

  Request = Struct.new(:request_method, :path, :query_string, :host, :port) do
    def [](name) = name == 'host' ? host : nil
    def ssl? = true
  end
  class Response
    attr_accessor :status, :body
    attr_reader :headers
    def initialize = @headers = {}
    def []=(key, value)
      @headers[key] = value
    end
    def [](key) = @headers[key]
  end

  def request(method = 'GET') = Request.new(method, '/api/megast', '', 'localhost', 443)

  def test_bridge_get
    res = Response.new
    app = lambda do |env|
      assert_equal 'GET', env['REQUEST_METHOD']
      assert_equal '/api/megast', env['PATH_INFO']
      assert_equal 'https', env['rack.url_scheme']
      assert_equal '', env['rack.input'].read
      [200, {'Content-Type' => 'application/json'}, ['{"ok":true}']]
    end
    QikvrtRailsBridge.call(app, request, res)
    assert_equal 200, res.status
    assert_equal '{"ok":true}', res.body
    assert_equal 'no-store', res['Cache-Control']
  end

  def test_bridge_head
    res = Response.new
    QikvrtRailsBridge.call(->(_) { [200, {}, ['not emitted']] }, request('HEAD'), res)
    assert_equal 200, res.status
    assert_equal '', res.body
  end

  def test_bridge_rejects_write_methods_before_calling_app
    %w[POST PUT PATCH DELETE OPTIONS].each do |method|
      res = Response.new
      QikvrtRailsBridge.call(->(_) { flunk 'app must not execute' }, request(method), res)
      assert_equal 405, res.status
      assert_equal 'GET, HEAD', res['Allow']
      assert_equal false, JSON.parse(res.body)['effect_ack_done']
    end
  end

  def test_bridge_closes_body_even_on_oversize
    body = Object.new
    body.define_singleton_method(:each) { |&block| block.call('x' * 65_537) }
    closed = false
    body.define_singleton_method(:close) { closed = true }
    assert_raises(RangeError) do
      QikvrtRailsBridge.call(->(_) { [200, {}, body] }, request, Response.new)
    end
    assert closed
  end

  def test_bridge_overrides_accidental_cache_header
    res = Response.new
    QikvrtRailsBridge.call(->(_) { [200, {'Cache-Control' => 'public, max-age=3600'}, ['ok']] }, request, res)
    assert_equal 'no-store', res['Cache-Control']
  end
  def test_real_webrick_request_and_response
    req = WEBrick::HTTPRequest.new(WEBrick::Config::HTTP)
    req.parse(StringIO.new("GET /api/megast HTTP/1.1\r\nHost: localhost\r\n\r\n"))
    res = WEBrick::HTTPResponse.new(WEBrick::Config::HTTP)
    app = lambda do |env|
      assert_equal '/api/megast', env['PATH_INFO']
      assert_equal 'http', env['rack.url_scheme']
      [200, {'content-type' => 'application/json', 'cache-control' => 'public'}, [JSON.generate(QikvrtMegaST.descriptor({}))]]
    end
    QikvrtRailsBridge.call(app, req, res)
    assert_equal 200, res.status
    assert_equal 'no-store', res['cache-control']
    assert_equal false, JSON.parse(res.body)['boundaries']['effect_ack_done']
  end

end
