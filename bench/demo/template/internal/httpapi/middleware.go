package httpapi

import (
	"fmt"
	"log"
	"net/http"
	"sync/atomic"
)

var requestSeq atomic.Int64

// withRequestID echoes X-Request-ID, or assigns one when the client sent none.
func withRequestID(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		id := r.Header.Get("X-Request-ID")
		if id == "" {
			id = fmt.Sprintf("req-%06d", requestSeq.Add(1))
		}
		w.Header().Set("X-Request-ID", id)
		next.ServeHTTP(w, r)
	})
}

// withRecover turns panics into 500 responses.
func withRecover(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		defer func() {
			if v := recover(); v != nil {
				log.Printf("panic serving %s %s: %v", r.Method, r.URL.Path, v)
				writeJSON(w, http.StatusInternalServerError, apiError{Error: "internal error", Code: "internal"})
			}
		}()
		next.ServeHTTP(w, r)
	})
}
