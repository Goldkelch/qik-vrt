# frozen_string_literal: true
# Copyright (c) 2026 Ingolf Lohmann. Repository licensing applies.
ENV['RAILS_ENV'] ||= 'production'
require 'bundler/setup'
require 'logger'
require 'rails'
require 'action_controller/railtie'
require_relative '../lib/megast'
require_relative '../lib/rails_bridge'

module QikvrtDelivery
  class Application < Rails::Application
    config.load_defaults 8.1
    config.root = File.expand_path('..', __dir__)
    config.api_only = true
    config.eager_load = true
    config.enable_reloading = false
    config.logger = Logger.new($stdout)
    config.log_level = :warn
    config.hosts = ['.vercel.app', 'localhost', '127.0.0.1']
    config.public_file_server.enabled = false
    config.consider_all_requests_local = false
    config.action_dispatch.show_exceptions = :rescuable
  end
end

class MegaStController < ActionController::API
  def show
    response.headers['Cache-Control'] = 'no-store'
    status = params[:qikvrt_operation] == 'download' ? :service_unavailable : :ok
    render json: QikvrtMegaST.descriptor, status: status
  end

  def download
    response.headers['Cache-Control'] = 'no-store'
    render json: QikvrtMegaST.descriptor, status: :service_unavailable
  end
end

QikvrtDelivery::Application.initialize!
QikvrtDelivery::Application.routes.draw do
  get '/api/megast', to: 'mega_st#show'
  get '/api/megast.rb', to: 'mega_st#show'
  get '/api/megast/download', to: 'mega_st#download'
end

Handler = proc do |request, response|
  QikvrtRailsBridge.call(QikvrtDelivery::Application, request, response)
end
