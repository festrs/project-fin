import axios from "axios";

const api = axios.create({
  baseURL: "/api",
  headers: {
    "X-User-Id": "ec92fcc7-1a95-4fa5-9911-7b88857cc524",
  },
});

export default api;
