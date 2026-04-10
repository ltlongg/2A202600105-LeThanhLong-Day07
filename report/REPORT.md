# Báo Cáo Lab 7: Embedding & Vector Store

**Họ tên:** Lê Thành Long  
**Nhóm:** C401 - B2  
**Ngày:** 2026-04-10

---

## 1. Warm-up (5 điểm)

### Cosine Similarity (Ex 1.1)

**High cosine similarity nghĩa là gì?**  
Theo em, khi hai chunk có cosine similarity cao thì có nghĩa là hai đoạn đó đang nói gần cùng một ý, hoặc ít nhất là cùng một chủ đề chính. Dù câu chữ có thể khác nhau nhưng embedding của chúng vẫn nằm khá gần nhau trong không gian vector.

**Ví dụ HIGH similarity:**
- Sentence A: `Pháp luật thi hành án hình sự là một ngành luật độc lập.`
- Sentence B: `Luật thi hành án hình sự điều chỉnh các quan hệ xã hội phát sinh trong quá trình thi hành án.`
- Tại sao tương đồng: Cả hai câu đều nói về bản chất và phạm vi điều chỉnh của pháp luật thi hành án hình sự.

**Ví dụ LOW similarity:**
- Sentence A: `Nguyên tắc nhân đạo nghiêm cấm hành vi xâm phạm nhân phẩm người chấp hành án.`
- Sentence B: `Thi hành án phạt tiền và án treo có thủ tục riêng.`
- Tại sao khác: Một câu nói về nguyên tắc nhân đạo, câu còn lại nói về một loại hình phạt và cách thi hành.

**Tại sao cosine similarity được ưu tiên hơn Euclidean distance cho text embeddings?**  
Cosine similarity phù hợp hơn vì nó so sánh hướng của vector, tức là so sánh mức độ giống nhau về ngữ nghĩa. Với text embeddings thì điều mình quan tâm thường là nội dung có gần nhau hay không, chứ không phải độ lớn tuyệt đối của vector.

### Chunking Math (Ex 1.2)

**Document 10,000 ký tự, chunk_size=500, overlap=50. Bao nhiêu chunks?**

```text
num_chunks = ceil((doc_length - overlap) / (chunk_size - overlap))
           = ceil((10000 - 50) / (500 - 50))
           = ceil(9950 / 450)
           = 23
```

**Đáp án:** `23 chunks`

**Nếu overlap tăng lên 100, chunk count thay đổi thế nào? Tại sao muốn overlap nhiều hơn?**

```text
num_chunks = ceil((10000 - 100) / (500 - 100))
           = ceil(9900 / 400)
           = 25
```

Khi overlap tăng từ `50` lên `100` thì số chunk tăng từ `23` lên `25`. Theo em, overlap lớn hơn sẽ có ích khi ý chính nằm gần mép chunk, vì nó giúp hai chunk liền nhau vẫn giữ được một phần ngữ cảnh chung.

---

## 2. Document Selection — Nhóm (10 điểm)

### Domain & Lý Do Chọn

**Domain:** Luật thi hành án hình sự

**Tại sao nhóm chọn domain này?**  
Nhóm em chọn domain này vì tài liệu luật có cấu trúc khá rõ theo chương, mục, tiểu mục nên rất phù hợp để thử chunking và metadata. Ngoài ra các câu hỏi benchmark cũng dễ kiểm chứng vì câu trả lời đều có thể đối chiếu trực tiếp từ nội dung văn bản.

### Data Inventory

Nhóm em dùng `law.md` làm nguồn chính. Để trình bày gọn và nhất quán, em chọn 5 chương đầu tiên của tài liệu làm 5 document units chính để gắn metadata và benchmark.

| # | Tên tài liệu | Nguồn | Số ký tự | Metadata đã gán |
|---|--------------|-------|----------|-----------------|
| 1 | Chương 1: Khái niệm, nhiệm vụ và nguồn của pháp luật thi hành án hình sự | Trích từ `law.md` | 22104 | `chapter=1`, `source=law.md`, `language=vi` |
| 2 | Chương 2: Các nguyên tắc cơ bản của pháp luật thi hành án hình sự | Trích từ `law.md` | 26455 | `chapter=2`, `source=law.md`, `language=vi` |
| 3 | Chương 3: Địa vị pháp lý của người bị kết án | Trích từ `law.md` | 46736 | `chapter=3`, `source=law.md`, `language=vi` |
| 4 | Chương 4: Hệ thống các cơ quan thi hành án hình sự | Trích từ `law.md` | 15628 | `chapter=4`, `source=law.md`, `language=vi` |
| 5 | Chương 5: Kiểm tra, giám sát hoạt động của các cơ quan thi hành án hình sự | Trích từ `law.md` | 16692 | `chapter=5`, `source=law.md`, `language=vi` |

### Metadata Schema

| Trường metadata | Kiểu | Ví dụ giá trị | Tại sao hữu ích cho retrieval? |
|----------------|------|---------------|-------------------------------|
| `chapter` | `str` | `2` | Giúp lọc nhanh theo chương khi câu hỏi bám rất rõ vào một chương |
| `section` | `str` | `2.3. Nguyên tắc nhân đạo` | Hữu ích với tài liệu luật vì mỗi câu hỏi thường map vào một mục khá cụ thể |
| `source` | `str` | `law.md` | Giúp truy vết lại tài liệu gốc |
| `language` | `str` | `vi` | Giữ thống nhất với query tiếng Việt |

---

## 3. Chunking Strategy — Cá nhân chọn, nhóm so sánh (15 điểm)

### Baseline Analysis

Em chạy `ChunkingStrategyComparator().compare()` trên 3 mục quan trọng trong `law.md` với `chunk_size=800`.

| Tài liệu | Strategy | Chunk Count | Avg Length | Preserves Context? |
|-----------|----------|-------------|------------|-------------------|
| `1.1. Khái niệm pháp luật thi hành án hình sự` | FixedSizeChunker (`fixed_size`) | 11 | 798.82 | Trung bình |
| `1.1. Khái niệm pháp luật thi hành án hình sự` | SentenceChunker (`by_sentences`) | 5 | 1582.20 | Giữ ý tốt nhưng chunk quá dài |
| `1.1. Khái niệm pháp luật thi hành án hình sự` | RecursiveChunker (`recursive`) | 13 | 635.92 | Tốt |
| `2.3. Nguyên tắc nhân đạo` | FixedSizeChunker (`fixed_size`) | 4 | 701.75 | Trung bình |
| `2.3. Nguyên tắc nhân đạo` | SentenceChunker (`by_sentences`) | 2 | 1327.50 | Dễ đọc nhưng hơi dài |
| `2.3. Nguyên tắc nhân đạo` | RecursiveChunker (`recursive`) | 6 | 441.50 | Tốt |
| `2. Nhiệm vụ của pháp luật thi hành án hình sự` | FixedSizeChunker (`fixed_size`) | 3 | 745.00 | Trung bình |
| `2. Nhiệm vụ của pháp luật thi hành án hình sự` | SentenceChunker (`by_sentences`) | 2 | 1064.50 | Ý trọn nhưng dài |
| `2. Nhiệm vụ của pháp luật thi hành án hình sự` | RecursiveChunker (`recursive`) | 4 | 532.25 | Tốt |

### Strategy Của Tôi

**Loại:** `RecursiveChunker(chunk_size=800)` kết hợp metadata `section`

**Mô tả cách hoạt động:**  
Em dùng `RecursiveChunker(chunk_size=800)` để tách văn bản theo thứ tự ưu tiên từ phần lớn đến phần nhỏ hơn, ví dụ tách theo xuống dòng đôi, xuống dòng đơn, rồi mới đến câu hoặc khoảng trắng nếu cần. Sau đó em gắn thêm metadata `chapter` và `section` dựa trên heading trong `law.md`. Với tài liệu luật, em thấy cách này hợp hơn vì chunk thường giữ được trọn một ý hoặc một tiểu mục thay vì bị cắt cứng theo số ký tự.

**Tại sao tôi chọn strategy này cho domain nhóm?**  
Tài liệu luật thường dài và chia rất rõ theo chương, mục, tiểu mục. Nếu chỉ dùng chunk theo ký tự thì dễ bị lẫn giữa các đoạn gần nhau, còn nếu tách đệ quy theo cấu trúc văn bản rồi kết hợp thêm metadata `section` thì lúc search sẽ dễ khoanh đúng phần cần tìm hơn. Ngoài ra, khi em thử chunk theo câu thì nhiều chunk vẫn khá dài vì câu trong tài liệu luật thường dài và chứa nhiều vế.

**Code snippet (nếu custom):**
```python
chunker = RecursiveChunker(chunk_size=800)

# Khi index thêm metadata:
metadata = {
    "chapter": chapter_id,
    "section": section_heading,
    "source": "law.md",
    "language": "vi",
}
```

### So Sánh: Strategy của tôi vs Baseline

Em benchmark trên 5 query của nhóm. Kết quả tổng quát:

| Tài liệu | Strategy | Chunk Count | Avg Length | Retrieval Quality? |
|-----------|----------|-------------|------------|--------------------|
| `law.md` + metadata `section` | Best baseline: `FixedSizeChunker(chunk_size=800, overlap=100)` | 399 | khoảng 800 ký tự/chunk | `8/10` |
| `law.md` + metadata `section` | **Của tôi: `RecursiveChunker(chunk_size=800)`** | 482 | khoảng 450-650 ký tự/chunk tùy mục | **`8/10`** |

### So Sánh Với Thành Viên Khác

Sau khi nhóm tổng hợp lại benchmark nội bộ, em cập nhật bảng so sánh giữa em và các thành viên khác như sau:

| Thành viên / cấu hình | Strategy | Retrieval Score (/10) | Điểm mạnh | Điểm yếu |
|-----------|----------|----------------------|-----------|----------|
| Lê Thành Long | `RecursiveChunker(chunk_size=800)` + metadata `section` | 8/10 | Dễ triển khai, vẫn bám được heading và đoạn trong `law.md`, phù hợp để làm baseline cá nhân ổn định | Chưa bám sát cấu trúc điều, khoản như các custom strategy nên một số query khó vẫn chưa trúng top-1 |
| Đỗ Xuân Bằng | `CustomChunker (Header)` | 9.5/10 | Gom khá trọn vẹn ý nghĩa của nguyên một điều luật, hạn chế bị xé ngữ cảnh | Có nguy cơ tạo chunk dài vượt mức nếu một điều luật quá dài |
| Đỗ Việt Anh | `CustomStrategy (Hybrid)` | 9.8/10 | Bảo toàn tốt tính bao đóng của điều, khoản; có sliding window nên xử lý điều dài vẫn giữ được gối đầu ngữ cảnh | Độ phức tạp tính toán cao hơn một chút so với các phương pháp thuần túy |
| Lã Thị Linh | `LegalArticleChunker (custom)` | 6.5/10 | Bám cấu trúc pháp lý tốt khi tài liệu đúng format | Khá nhạy với format tài liệu, cần regex robust hơn |
| Trương Anh Long | `Custom (by sections)` | 9/10 | Giữ nguyên ngữ nghĩa theo từng điều, chương; hạn chế bị cắt nhỏ làm mất context | Phụ thuộc mạnh vào cấu trúc văn bản, khó áp dụng cho dữ liệu phi cấu trúc |

**Strategy nào tốt nhất cho domain này? Tại sao?**  
Nếu xét theo benchmark của nhóm thì các strategy custom bám cấu trúc điều, khoản, chương của văn bản luật đang cho kết quả tốt hơn rõ rệt so với các chunker generic. Trong đó, `CustomStrategy (Hybrid)` cho điểm cao nhất vì vừa giữ được tính trọn nghĩa của điều luật, vừa có cơ chế gối đầu để không mất ngữ cảnh khi điều quá dài. Tuy vậy, với implementation cá nhân của em trong phạm vi lab này, `RecursiveChunker` vẫn là một lựa chọn khá cân bằng vì dễ triển khai hơn, không phụ thuộc quá mạnh vào format tài liệu nhưng vẫn tận dụng được cấu trúc heading của `law.md`.

---

## 4. My Approach — Cá nhân (10 điểm)

### Chunking Functions

**`RecursiveChunker.chunk` / `_split`** — approach:  
Em để recursive chunking thử tách theo thứ tự từ separator lớn xuống nhỏ như xuống dòng đôi, xuống dòng đơn, dấu chấm, khoảng trắng. Nếu một đoạn vẫn quá dài thì tiếp tục tách nhỏ hơn để bảo đảm chunk không vượt ngưỡng nhưng vẫn giữ được ngữ cảnh tốt nhất có thể.

**Vì sao em ưu tiên hàm này trong lab:**  
Với `law.md`, nhiều ý được trình bày theo heading và đoạn dài. Recursive chunking giúp em giữ được khối nội dung theo cấu trúc văn bản thay vì ép theo số câu cố định.

### EmbeddingStore

**`add_documents` + `search`** — approach:  
Em lưu dữ liệu theo dạng `in-memory` vì đề cho phép `in-memory or ChromaDB` và máy em không chạy ổn ChromaDB. Mỗi chunk sẽ được lưu cùng `content`, `embedding`, `metadata`, sau đó search bằng cách embed query và chấm điểm theo dot product.

**`search_with_filter` + `delete_document`** — approach:  
Em dùng `search_with_filter()` để lọc trước theo `section` hoặc `chapter`, vì với tài liệu luật metadata kiểu này hữu ích hơn lọc sau. `delete_document()` thì xóa toàn bộ chunk có cùng `doc_id`.

### KnowledgeBaseAgent

**`answer`** — approach:  
Agent sẽ lấy top-k chunk trước, ghép các chunk đó vào prompt làm context, rồi mới gọi hàm LLM. Em để prompt theo hướng bắt buộc trả lời dựa trên context, nếu thiếu dữ liệu thì phải nói rõ là chưa đủ thông tin.

### Test Results

```text
42 passed, 1 warning in 0.55s
```

**Số tests pass:** `42 / 42`

---

## 5. Similarity Predictions — Cá nhân (5 điểm)

| Pair | Sentence A | Sentence B | Dự đoán | Actual Score | Đúng? |
|------|-----------|-----------|---------|--------------|-------|
| 1 | Pháp luật thi hành án hình sự là một ngành luật độc lập. | Luật thi hành án hình sự điều chỉnh các quan hệ xã hội phát sinh trong quá trình thi hành án. | high | 0.435 | Có |
| 2 | Nguyên tắc nhân đạo nghiêm cấm hành vi xâm phạm nhân phẩm người chấp hành án. | Pháp luật thi hành án hình sự phải tôn trọng danh dự và nhân phẩm của người bị kết án. | high | 0.477 | Có |
| 3 | Người bị kết án có quyền khiếu nại, tố cáo hành vi trái pháp luật. | Khi quyền lợi hợp pháp bị xâm phạm thì người chấp hành án được quyền tố cáo. | high | 0.473 | Có |
| 4 | Thi hành án hình sự phải bảo đảm bản án được thực hiện nghiêm chỉnh. | Pháp luật thi hành án hình sự còn có nhiệm vụ giáo dục người bị kết án tái hòa nhập cộng đồng. | low | 0.321 | Không |
| 5 | Nguyên tắc nhân đạo trong thi hành án hình sự. | Quy định về thi hành án phạt tiền và án treo. | low | 0.356 | Không |

**Kết quả nào bất ngờ nhất? Điều này nói gì về cách embeddings biểu diễn nghĩa?**  
Điều làm em bất ngờ nhất là pair 5. Em nghĩ hai câu này sẽ thấp hơn nhiều, nhưng kết quả vẫn khá dương. Theo em, điều này cho thấy `_mock_embed` chỉ mô phỏng tương đối chứ chưa phản ánh ngữ nghĩa sâu như embedding thật, nên khi làm bài vẫn cần nhìn cả chunk thực tế chứ không nên chỉ nhìn score.

---

## 6. Results — Cá nhân (10 điểm)

Em chạy 5 benchmark queries của nhóm trên `law.md`, dùng `RecursiveChunker(chunk_size=800)` và thêm metadata `section` để lọc đúng mục liên quan.

### Benchmark Queries & Gold Answers (nhóm thống nhất)

| # | Query | Gold Answer |
|---|-------|-------------|
| 1 | Khái niệm pháp luật thi hành án hình sự là gì? | Là tổng hợp các quy phạm pháp luật điều chỉnh các quan hệ xã hội phát sinh trong quá trình thi hành án. |
| 2 | Nguyên tắc nhân đạo trong thi hành án hình sự thể hiện như thế nào? | Không đối xử tàn bạo, bảo đảm pháp lý cho cuộc sống người bị kết án, tôn trọng quyền con người. |
| 3 | Tác dụng giáo dục cải tạo của hình phạt là gì? | Giáo dục cải tạo họ thành người lương thiện, tuân thủ pháp luật và có ích cho xã hội. |
| 4 | Nhiệm vụ của pháp luật thi hành án hình sự là gì? | Bảo đảm bản án được thực thi nghiêm minh, tạo điều kiện cho người thụ án tái hòa nhập cộng đồng. |
| 5 | Các quyền lợi hợp pháp bị xâm phạm thì người bị kết án giải quyết thế nào? | Có quyền khiếu nại, tố cáo đối với hành vi xâm phạm của cơ quan hoặc cá nhân thi hành án. |

### Kết Quả Của Tôi

| # | Query | Top-1 Retrieved Chunk (tóm tắt) | Score | Relevant? | Agent Answer (tóm tắt) |
|---|-------|--------------------------------|-------|-----------|------------------------|
| 1 | Khái niệm pháp luật thi hành án hình sự là gì? | Chunk rơi đúng vào mục `1.1. Khái niệm pháp luật thi hành án hình sự`, nêu rõ đây là tổng hợp các quy phạm điều chỉnh quan hệ phát sinh trong quá trình thi hành án | 0.600 | Có | Pháp luật thi hành án hình sự là ngành luật điều chỉnh các quan hệ xã hội phát sinh trong quá trình thi hành án hình sự |
| 2 | Nguyên tắc nhân đạo trong thi hành án hình sự thể hiện như thế nào? | Chunk rơi vào mục `2.3. Nguyên tắc nhân đạo`, nói rõ việc tôn trọng danh dự, nhân phẩm và bảo đảm điều kiện pháp lý cho người bị kết án | 0.744 | Có | Nguyên tắc nhân đạo thể hiện ở việc không đối xử tàn bạo, tôn trọng quyền con người và bảo đảm điều kiện sống, học tập, cải tạo cho người bị kết án |
| 3 | Tác dụng giáo dục cải tạo của hình phạt là gì? | Chunk liên quan đến phần “cải tạo, giáo dục người bị kết án”, nhấn mạnh mục tiêu giúp họ trở thành người có ích cho xã hội | 0.623 | Có | Giáo dục cải tạo nhằm giúp người bị kết án sửa chữa sai lầm, trở thành người lương thiện, có ý thức tuân thủ pháp luật và tái hòa nhập cộng đồng |
| 4 | Nhiệm vụ của pháp luật thi hành án hình sự là gì? | Chunk mở đầu đúng mục `2. NHIỆM VỤ CỦA PHÁP LUẬT THI HÀNH ÁN HÌNH SỰ`, nên trả lời khá sát ý hỏi | 0.701 | Có | Nhiệm vụ của pháp luật thi hành án hình sự là bảo đảm bản án được thi hành nghiêm minh, đồng thời giáo dục người bị kết án và hỗ trợ họ tái hòa nhập cộng đồng |
| 5 | Các quyền lợi hợp pháp bị xâm phạm thì người bị kết án giải quyết thế nào? | Top-1 vẫn mới lấy trúng chunk khá chung về quyền và nguyên tắc, chưa chạm đúng cụm “khiếu nại, tố cáo” | 0.217 | Chưa | Câu trả lời agent còn chung, chưa truy ra đúng đoạn quy định trực tiếp về quyền khiếu nại, tố cáo |

**Bao nhiêu queries trả về chunk relevant trong top-3?** `4 / 5`

---

## 7. What I Learned (5 điểm — Demo)

**Điều hay nhất tôi học được từ thành viên khác trong nhóm:**  
Qua so sánh với các bạn trong nhóm, điều em học được rõ nhất là với dữ liệu luật thì chunking bám cấu trúc pháp lý quan trọng hơn các phương pháp chunking generic. Cụ thể, cách làm của bạn Đỗ Việt Anh dùng `CustomStrategy (Hybrid)` cho em thấy nếu vừa giữ được tính trọn nghĩa của từng điều, khoản, vừa có sliding window để gối đầu ngữ cảnh, thì chất lượng retrieval sẽ tốt hơn rõ rệt. Ngoài ra, cách làm của bạn Đỗ Xuân Bằng và bạn Trương Anh Long cũng cho thấy khi chunk theo header hoặc theo section, hệ thống sẽ ít bị cắt mất ý hơn và câu trả lời sát với văn bản luật hơn.

**Điều hay nhất tôi học được từ nhóm khác (qua demo):**  
Từ phần demo và so sánh giữa các cách làm, em rút ra rằng với văn bản có cấu trúc chặt như tài liệu luật, việc tận dụng heading, điều, khoản và mục nhỏ gần như quyết định chất lượng retrieval. Nếu chỉ dùng chunk theo độ dài hoặc theo câu thì hệ thống vẫn chạy được, nhưng khi truy vấn đi vào các quyền, nghĩa vụ hoặc nguyên tắc rất cụ thể thì dễ lấy nhầm đoạn có từ khóa gần giống mà chưa đúng trọng tâm.

**Nếu làm lại, tôi sẽ thay đổi gì trong data strategy?**  
Nếu làm lại, em sẽ tiền xử lý `law.md` kỹ hơn bằng cách loại bỏ phần bìa, mục lục và các đoạn tham khảo trước khi index. Sau đó em sẽ tách tài liệu theo cấu trúc pháp lý chi tiết hơn, ví dụ thêm metadata như `chapter`, `section`, `article_like_heading` hoặc `subsection`, thay vì chỉ dừng ở mức `section`. Em cũng muốn thử một chiến lược hybrid: ưu tiên tách theo heading trước, sau đó nếu một mục quá dài thì mới dùng sliding window hoặc recursive chunking để giữ thêm ngữ cảnh.

### Failure Analysis

Failure case rõ nhất của em vẫn là query số 5 về quyền khiếu nại, tố cáo khi quyền lợi hợp pháp bị xâm phạm. Kết quả này cho thấy `RecursiveChunker` tuy khá ổn với văn bản luật, nhưng vẫn chưa đủ mạnh khi câu hỏi yêu cầu truy đúng một ý pháp lý rất cụ thể. Theo em, nguyên nhân chính là metadata còn hơi thô và chunk chưa bám sát đến mức tiểu mục nhỏ. Nếu cải thiện lại, em sẽ thử chunk theo heading pháp lý chi tiết hơn hoặc thêm cơ chế gối đầu ngữ cảnh cho các đoạn liệt kê quyền và nghĩa vụ.

---

## Tự Đánh Giá

| Tiêu chí | Loại | Điểm tự đánh giá |
|----------|------|-------------------|
| Warm-up | Cá nhân | 5 / 5 |
| Document selection | Nhóm | 9 / 10 |
| Chunking strategy | Nhóm | 13 / 15 |
| My approach | Cá nhân | 10 / 10 |
| Similarity predictions | Cá nhân | 4 / 5 |
| Results | Cá nhân | 8 / 10 |
| Core implementation (tests) | Cá nhân | 30 / 30 |
| Demo | Nhóm | 5 / 5 |
| **Tổng** | | **84 / 90** |
