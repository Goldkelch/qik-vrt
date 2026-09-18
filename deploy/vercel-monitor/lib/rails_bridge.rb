# frozen_string_literal: true
# Copyright (c) 2026 Ingolf Lohmann. Repository licensing applies.
require 'json'
require 'stringio'

module QikvrtRailsBridge
  MAX_RESPONSE_BYTES = 65_536

  # Adapt Vercel's documented WEBrick request/response pair to a Rack app.
  # No request body, shell execution, background job or upstream fetch is used.
  def self.call(app, request, response)
    response['Cache-Control'] = 'no-store'
    response['X-QIKVRT-Role'] = 'READ_ONLY_SOURCE_DESCRIPTOR'
    method = request.request_method
    unless %w[GET HEAD].include?(method)
      response.status = 405
      response['Allow'] = 'GET, HEAD'
      response['Content-Type'] = 'application/json; charset=utf-8'
      response.body = JSON.generate(error: 'METHOD_NOT_ALLOWED', effect_ack_done: false)
      return
    end
    env = {
      'REQUEST_METHOD' => method,
      'SCRIPT_NAME' => '',
      'PATH_INFO' => request.path,
      'QUERY_STRING' => request.query_string.to_s,
      'SERVER_NAME' => request.host,
      'SERVER_PORT' => request.port.to_s,
      'SERVER_PROTOCOL' => 'HTTP/1.1',
      'HTTP_HOST' => request['host'].to_s,
      'HTTPS' => request.ssl? ? 'on' : 'off',
      'rack.url_scheme' => request.ssl? ? 'https' : 'http',
      'rack.input' => StringIO.new(''),
      'rack.errors' => $stderr
    }
    body = nil
    status, headers, body = app.call(env)
    bytes = String.new
    body.each do |chunk|
      raise TypeError, 'Rack response must contain strings' unless chunk.is_a?(String)
      raise RangeError, 'descriptor response too large' if bytes.bytesize + chunk.bytesize > MAX_RESPONSE_BYTES
      bytes << chunk
    end
    response.status = status
    headers.each { |key, value| response[key] = value }
    # Do not let Rails ETags or a handler override the no-stale-evidence policy.
    response['Cache-Control'] = 'no-store'
    response['X-QIKVRT-Role'] = 'READ_ONLY_SOURCE_DESCRIPTOR'
    response.body = method == 'HEAD' ? '' : bytes
  ensure
    body.close if body.respond_to?(:close)
  end
end
