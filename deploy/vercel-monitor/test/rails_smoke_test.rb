# frozen_string_literal: true
# This test deliberately fails rather than skips when Rails is unavailable.
require 'securerandom'
# Exercise production middleware with a fresh, test-process-only signing key.
# Never reuse a deployment credential or add a fallback to application code.
ENV['RAILS_ENV'] = 'production'
ENV['SECRET_KEY_BASE'] = SecureRandom.hex(64)
require 'minitest/autorun'
require 'rack/mock'
require_relative '../api/megast'

class RailsSmokeTest < Minitest::Test
  def client = Rack::MockRequest.new(QikvrtDelivery::Application)
  def get(path) = client.get(path, 'HTTP_HOST' => 'localhost')

  def test_production_fixture
    assert Rails.env.production?
    assert QikvrtDelivery::Application.config.secret_key_base.to_s.bytesize >= 128
  end

  def test_rails_descriptor
    response = get('/api/megast')
    assert_equal 200, response.status
    assert_equal 'no-store', response['cache-control']
    assert_equal '2fdcf8d233b1495732ef38e3406ebfc095fd0ef3', JSON.parse(response.body)['source']['source_commit']
    assert_equal false, JSON.parse(response.body)['boundaries']['effect_ack_done']
  end

  def test_download_is_not_fabricated
    %w[/api/megast/download /api/megast.rb?qikvrt_operation=download].each do |path|
      response = get(path)
      assert_equal 503, response.status
      assert_nil JSON.parse(response.body)['delivery']['download_url']
    end
  end

  def test_head
    response = client.head('/api/megast', 'HTTP_HOST' => 'localhost')
    assert_equal 200, response.status
    assert_equal '', response.body
  end

  def test_host_authorization
    response = client.get('/api/megast', 'HTTP_HOST' => 'untrusted.example')
    assert_equal 403, response.status
  end
end
