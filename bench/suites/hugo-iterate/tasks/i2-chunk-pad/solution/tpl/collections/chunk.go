// Copyright 2024 The Hugo Authors. All rights reserved.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
// http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

package collections

import (
	"errors"
	"fmt"
	"reflect"

	"github.com/spf13/cast"
)

// Chunk splits l into consecutive chunks of the given size.
// The last chunk is shorter when the length of l is not a multiple of size,
// unless a pad value is given: the first one fills the last chunk up to size.
func (ns *Namespace) Chunk(size any, l any, pad ...any) ([][]any, error) {
	n, err := chunkSize(size)
	if err != nil {
		return nil, err
	}
	items, err := chunkItems(l)
	if err != nil {
		return nil, err
	}
	chunks := [][]any{}
	for i := 0; i < len(items); i += n {
		end := min(i+n, len(items))
		chunk := items[i:end]
		if len(pad) > 0 {
			for len(chunk) < n {
				chunk = append(chunk[:len(chunk):len(chunk)], pad[0])
			}
		}
		chunks = append(chunks, chunk)
	}
	return chunks, nil
}

func chunkSize(size any) (int, error) {
	n, err := cast.ToIntE(size)
	if err != nil || n < 1 {
		return 0, fmt.Errorf("size must be a positive integer, got %v", size)
	}
	return n, nil
}

func chunkItems(l any) ([]any, error) {
	lv, isNil := indirect(reflect.ValueOf(l))
	if isNil {
		return nil, errors.New("can't iterate over a nil value")
	}
	switch lv.Kind() {
	case reflect.Array, reflect.Slice:
		items := make([]any, lv.Len())
		for i := range items {
			items[i] = lv.Index(i).Interface()
		}
		return items, nil
	default:
		return nil, fmt.Errorf("can't iterate over %T", l)
	}
}
