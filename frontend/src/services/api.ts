import axios from "axios";

const api = axios.create({
  baseURL: "/api",
  headers: {
    "X-User-Id": "default-user-id",
  },
});

export default api;
