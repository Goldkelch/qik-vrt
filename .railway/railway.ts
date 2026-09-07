import {
  defineRailway,
  github,
  preserve,
  project,
  service,
  volume,
} from "railway/iac";

export default defineRailway(() => {
  const region = "europe-west4";
  const state = volume("qikvrt-terminal-state", {
    region,
    sizeMB: 5120,
  });

  const terminal = service("qikvrt-cloud-transputer", {
    source: github("Goldkelch/qik-vrt", {
      branch: "infra/qikvrt-cloud-transputer-v1",
    }),
    replicas: { [region]: 1 },
    healthcheck: "/healthz",
    healthcheckTimeout: 300,
    volumeMounts: {
      "/var/lib/qikvrt/state": state,
    },
    env: {
      PORT: "8080",
      RAILWAY_DOCKERFILE_PATH: "deploy/universal-terminal/Dockerfile",
      RAILWAY_RUN_UID: "10001",
      RAILWAY_SHM_SIZE_BYTES: "536870912",
      QIKVRT_PROFILE_DIR: "/var/lib/qikvrt/state/firefox-profile",
      QIKVRT_STATE_DIR: "/var/lib/qikvrt/state",
      QIKVRT_PROXY_HOST: "0.0.0.0",
      QIKVRT_PROXY_PORT: "8080",
      QIKVRT_PROXY_USERNAME: "qikvrt",
      QIKVRT_PROXY_PASSWORD: preserve(),
      QIKVRT_START_URL: "https://github.com/Goldkelch/qik-vrt",
      QIKVRT_MIRROR_REOBSERVE_SECONDS: "900",
    },
  });

  return project("qikvrt-cloud-transputer", {
    resources: [state, terminal],
  });
});
