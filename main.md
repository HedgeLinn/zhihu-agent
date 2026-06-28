# 构建知乎智能体
## 可迭代的按照搜索问题建立项目文件夹，输出对应的以及md 

# 知乎apikey
# 知乎skill压缩包
https://developer.zhihu.com/download/zhihu_search_skills.zip

该接口用于知乎站内内容搜索，返回与查询相关的问题、回答或文章结果。

接口信息
说明	值
HTTP URL	https://developer.zhihu.com/api/v1/content/zhihu_search
HTTP Method	GET
请求参数
Header
Authorization：Bearer <your_access_secret>
X-Request-Timestamp：秒级 Unix 时间戳
Content-Type：固定值 application/json
Query
名称	类型	必填	说明
Query	String	是	查询关键词
Count	Int32	否	请求数量，默认 10，最大 10
说明：

Query 不能为空。
当 Count <= 0 时，服务端默认回退为 10。
当 Count > 10 时，服务端会自动截断为 10。
响应参数
Data：

参数名	类型	是否必返	描述
HasMore	Bool	是	当前实现固定返回 false
SearchHashId	String	是	搜索请求标识
Items	Array[Item]	是	搜索结果列表
EmptyReason	String	否	无结果时的原因说明
Item：

参数名	类型	是否必返	描述
Title	String	是	内容标题
ContentType	String	是	内容类型
ContentID	String	是	内容标识
ContentText	String	是	内容摘要
Url	String	是	内容链接（带溯源 utm 参数）
CommentCount	Int32	是	评论数
VoteUpCount	Int32	是	赞同数
AuthorName	String	是	作者昵称
AuthorAvatar	String	是	作者头像
AuthorBadge	String	是	作者认证图标
AuthorBadgeText	String	是	作者认证文案
EditTime	Int32	是	发布时间或更新时间戳
CommentInfoList	Array[CommentInfo]	否	精选评论
AuthorityLevel	String	是	权威等级
RankingScore	Float32	是	排序分数
CommentInfo：

参数名	类型	是否必返	描述
Content	String	是	评论内容
